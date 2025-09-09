"""
RAG对话记忆模块
使用向量相似度检索相关历史对话，为AI提供上下文记忆
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np
from django.utils import timezone


@dataclass
class ConversationFragment:
    """对话片段"""
    id: str
    user_id: Optional[int]
    user_message: str
    ai_response: str
    timestamp: datetime
    context_type: str  # 'order_query', 'statistics', 'general', etc.
    keywords: List[str]
    embedding: Optional[np.ndarray] = None


class SimpleEmbedding:
    """简单的文本嵌入实现（基于TF-IDF和关键词）"""
    
    def __init__(self):
        self.vocabulary = set()
        self.idf_scores = {}
        
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的中文关键词提取
        import re
        
        # 移除标点符号，保留中文、英文和数字
        cleaned = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s]', ' ', text.lower())
        
        # 分词（简单按空格分割，实际项目中可以使用jieba等）
        words = cleaned.split()
        
        # 过滤停用词和短词
        stop_words = {'的', '了', '是', '在', '有', '和', '与', '或', '但', '不', '没', '也', '都', '很', '最', '更', '我', '你', '他', '她', '它'}
        keywords = [word for word in words if len(word) > 1 and word not in stop_words]
        
        return keywords
    
    def _calculate_tf_idf(self, keywords: List[str], all_keywords: List[List[str]]) -> np.ndarray:
        """计算TF-IDF向量"""
        # 简化的TF-IDF实现
        vocab_size = len(self.vocabulary)
        if vocab_size == 0:
            return np.zeros(100)  # 返回固定长度的零向量
        
        # 创建词汇表索引
        vocab_list = list(self.vocabulary)
        vocab_dict = {word: i for i, word in enumerate(vocab_list)}
        
        # 计算TF
        tf_vector = np.zeros(min(vocab_size, 100))  # 限制向量长度
        for keyword in keywords:
            if keyword in vocab_dict and vocab_dict[keyword] < 100:
                tf_vector[vocab_dict[keyword]] += 1
        
        # 标准化
        if np.sum(tf_vector) > 0:
            tf_vector = tf_vector / np.sum(tf_vector)
        
        return tf_vector
    
    def encode(self, text: str, all_texts: List[str] = None) -> np.ndarray:
        """对文本进行编码"""
        keywords = self._extract_keywords(text)
        
        # 更新词汇表
        self.vocabulary.update(keywords)
        
        # 如果提供了所有文本，计算TF-IDF
        if all_texts:
            all_keywords = [self._extract_keywords(t) for t in all_texts]
            return self._calculate_tf_idf(keywords, all_keywords)
        
        # 否则返回简单的词频向量
        return self._simple_encoding(keywords)
    
    def _simple_encoding(self, keywords: List[str]) -> np.ndarray:
        """简单编码：基于关键词哈希"""
        vector = np.zeros(100)
        for keyword in keywords:
            # 使用哈希函数将关键词映射到向量位置
            hash_val = int(hashlib.md5(keyword.encode()).hexdigest(), 16)
            idx = hash_val % 100
            vector[idx] += 1
        
        # 标准化
        if np.sum(vector) > 0:
            vector = vector / np.sum(vector)
        
        return vector


class ConversationMemory:
    """对话记忆管理器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.join(os.path.dirname(__file__), 'conversation_memory.db')
        self.embedding_model = SimpleEmbedding()
        self.init_database()
        
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                context_type TEXT,
                keywords TEXT,
                embedding BLOB
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id ON conversations(user_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp ON conversations(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_context_type ON conversations(context_type)
        ''')
        
        conn.commit()
        conn.close()
    
    def store_conversation(self, user_message: str, ai_response: str, user_id: Optional[int] = None, context_type: str = 'general') -> str:
        """存储对话片段"""
        # 生成唯一ID
        conversation_id = hashlib.md5(f"{user_message}{ai_response}{timezone.now().isoformat()}".encode()).hexdigest()
        
        # 提取关键词
        combined_text = f"{user_message} {ai_response}"
        keywords = self.embedding_model._extract_keywords(combined_text)
        
        # 生成嵌入向量
        embedding = self.embedding_model.encode(combined_text)
        
        # 存储到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO conversations 
            (id, user_id, user_message, ai_response, timestamp, context_type, keywords, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conversation_id,
            user_id,
            user_message,
            ai_response,
            timezone.now().isoformat(),
            context_type,
            json.dumps(keywords, ensure_ascii=False),
            embedding.tobytes()
        ))
        
        conn.commit()
        conn.close()
        
        return conversation_id
    
    def retrieve_relevant_conversations(self, query: str, user_id: Optional[int] = None, limit: int = 3, similarity_threshold: float = 0.1) -> List[ConversationFragment]:
        """检索相关的历史对话"""
        # 对查询进行编码
        query_embedding = self.embedding_model.encode(query)
        
        # 从数据库获取候选对话
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询条件
        query_conditions = []
        params = []
        
        if user_id is not None:
            query_conditions.append("user_id = ?")
            params.append(user_id)
        
        # 只获取最近30天的对话
        thirty_days_ago = (timezone.now() - timedelta(days=30)).isoformat()
        query_conditions.append("timestamp > ?")
        params.append(thirty_days_ago)
        
        where_clause = " AND ".join(query_conditions) if query_conditions else "1=1"
        
        cursor.execute(f'''
            SELECT id, user_id, user_message, ai_response, timestamp, context_type, keywords, embedding
            FROM conversations 
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT 50
        ''', params)
        
        rows = cursor.fetchall()
        conn.close()
        
        # 计算相似度并排序
        relevant_conversations = []
        
        for row in rows:
            try:
                stored_embedding = np.frombuffer(row[7], dtype=np.float64)
                
                # 计算余弦相似度
                similarity = self._calculate_cosine_similarity(query_embedding, stored_embedding)
                
                if similarity > similarity_threshold:
                    fragment = ConversationFragment(
                        id=row[0],
                        user_id=row[1],
                        user_message=row[2],
                        ai_response=row[3],
                        timestamp=datetime.fromisoformat(row[4]),
                        context_type=row[5],
                        keywords=json.loads(row[6]) if row[6] else [],
                        embedding=stored_embedding
                    )
                    relevant_conversations.append((similarity, fragment))
            except Exception as e:
                print(f"处理对话片段时出错: {e}")
                continue
        
        # 按相似度排序并返回前N个
        relevant_conversations.sort(key=lambda x: x[0], reverse=True)
        return [conv[1] for conv in relevant_conversations[:limit]]
    
    def _calculate_cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算余弦相似度"""
        try:
            # 确保向量长度一致
            min_len = min(len(vec1), len(vec2))
            vec1 = vec1[:min_len]
            vec2 = vec2[:min_len]
            
            # 计算余弦相似度
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            return dot_product / (norm1 * norm2)
        except Exception:
            return 0.0
    
    def get_user_conversation_summary(self, user_id: int, days: int = 7) -> Dict[str, Any]:
        """获取用户对话摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        since_date = (timezone.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT context_type, COUNT(*) as count, MAX(timestamp) as last_time
            FROM conversations 
            WHERE user_id = ? AND timestamp > ?
            GROUP BY context_type
            ORDER BY count DESC
        ''', (user_id, since_date))
        
        context_stats = cursor.fetchall()
        
        cursor.execute('''
            SELECT COUNT(*) FROM conversations 
            WHERE user_id = ? AND timestamp > ?
        ''', (user_id, since_date))
        
        total_conversations = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_conversations': total_conversations,
            'context_distribution': [
                {'type': row[0], 'count': row[1], 'last_time': row[2]}
                for row in context_stats
            ],
            'days': days
        }
    
    def clean_old_conversations(self, days_to_keep: int = 90):
        """清理旧的对话记录"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff_date = (timezone.now() - timedelta(days=days_to_keep)).isoformat()
        
        cursor.execute('DELETE FROM conversations WHERE timestamp < ?', (cutoff_date,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count 
/**
 * WebSocket客户端 - 实时通知功能
 */
class WebSocketClient {
    constructor() {
        this.socket = null;
        this.reconnectInterval = 3000; // 重连间隔（毫秒）
        this.maxReconnectAttempts = 5;
        this.reconnectAttempts = 0;
        this.isConnected = false;
        this.messageHandlers = {};
        this.init();
    }

    init() {
        this.connect();
        this.setupEventHandlers();
    }

    connect() {
        try {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/notifications/`;
            
            this.socket = new WebSocket(wsUrl);
            this.bindSocketEvents();
        } catch (error) {
            console.error('WebSocket连接失败:', error);
            this.handleReconnect();
        }
    }

    bindSocketEvents() {
        this.socket.onopen = (event) => {
            console.log('WebSocket连接已建立');
            this.isConnected = true;
            this.reconnectAttempts = 0;
            this.updateConnectionStatus(true);
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('消息解析失败:', error);
            }
        };

        this.socket.onclose = (event) => {
            console.log('WebSocket连接已关闭');
            this.isConnected = false;
            this.updateConnectionStatus(false);
            this.handleReconnect();
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket错误:', error);
            this.isConnected = false;
            this.updateConnectionStatus(false);
        };
    }

    handleMessage(data) {
        const messageType = data.type;
        
        switch (messageType) {
            case 'connection_established':
                this.showNotification('连接成功', 'success');
                break;
            case 'order_notification':
                this.handleOrderNotification(data.data);
                break;
            case 'progress_notification':
                this.handleProgressNotification(data.data);
                break;
            case 'dashboard_update':
                this.handleDashboardUpdate(data.data);
                break;
            case 'general_notification':
                this.handleGeneralNotification(data.data);
                break;
            default:
                console.log('未知消息类型:', messageType, data);
        }
    }

    handleOrderNotification(data) {
        let message = '';
        if (data.action === 'created') {
            message = `新订单创建: ${data.order_no} - ${data.customer_name}`;
        } else if (data.action === 'updated') {
            message = `订单更新: ${data.order_no} - ${data.status_display}`;
        } else if (data.action === 'deleted') {
            message = `订单删除: ${data.order_no}`;
        }
        
        this.showNotification(message, 'info');
        this.updateOrderList();
    }

    handleProgressNotification(data) {
        let message = '';
        if (data.action === 'created') {
            message = `新进度步骤: ${data.order_no} - ${data.step_name}`;
        } else if (data.action === 'updated') {
            message = `进度更新: ${data.order_no} - ${data.step_name} (${data.status_display})`;
        }
        
        this.showNotification(message, 'info');
        this.updateProgressList();
    }

    handleDashboardUpdate(data) {
        this.updateDashboardStats(data);
        
        // 如果在仪表板或首页，也显示通知并刷新
        if (window.location.pathname.includes('/print-dashboard/') || window.location.pathname.includes('/index/')) {
            this.showNotification('📊 仪表板数据已更新', 'info');
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        }
    }

    handleGeneralNotification(data) {
        this.showNotification(data.message, data.type);
    }

    updateDashboardStats(data) {
        // 更新仪表板统计数据
        const elements = {
            'total_orders': document.getElementById('total-orders'),
            'pending_orders': document.getElementById('pending-orders'),
            'processing_orders': document.getElementById('processing-orders'),
            'completed_orders': document.getElementById('completed-orders'),
            'current_steps_count': document.getElementById('current-steps-count'),
            'next_steps_count': document.getElementById('next-steps-count'),
            'urgent_orders_count': document.getElementById('urgent-orders-count')
        };

        for (const [key, element] of Object.entries(elements)) {
            if (element && data[key] !== undefined) {
                element.textContent = data[key];
            }
        }
    }

    updateOrderList() {
        // 刷新订单列表
        console.log('🔄 更新订单列表');
        
        // 如果在订单列表页面，重新加载页面
        if (window.location.pathname.includes('/print-orders/') || window.location.pathname.includes('/index/')) {
            setTimeout(() => {
                window.location.reload();
            }, 1000); // 延迟1秒刷新，让通知先显示
        }
    }

    updateProgressList() {
        // 刷新进度列表
        console.log('🔄 更新进度列表');
        
        // 如果在进度相关页面，重新加载页面
        if (window.location.pathname.includes('/progress/') || 
            window.location.pathname.includes('/print-orders/') ||
            window.location.pathname.includes('/index/') ||
            window.location.pathname.includes('/print-dashboard/')) {
            setTimeout(() => {
                window.location.reload();
            }, 1000); // 延迟1秒刷新，让通知先显示
        }
    }

    showNotification(message, type = 'info') {
        // 显示通知
        console.log(`[${type.toUpperCase()}] ${message}`);
        
        // 如果页面有通知容器，显示通知
        const notificationContainer = document.getElementById('notification-container');
        if (notificationContainer) {
            const notification = document.createElement('div');
            notification.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : 'info'} alert-dismissible fade show`;
            notification.innerHTML = `
                ${message}
                <button type="button" class="close" data-dismiss="alert">
                    <span>&times;</span>
                </button>
            `;
            notificationContainer.appendChild(notification);
            
            // 自动隐藏通知
            setTimeout(() => {
                notification.remove();
            }, 5000);
        }
    }

    updateConnectionStatus(connected) {
        const statusElement = document.getElementById('websocket-status');
        if (statusElement) {
            statusElement.textContent = connected ? '已连接' : '已断开';
            statusElement.className = connected ? 'text-success' : 'text-danger';
        }
    }

    handleReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => {
                this.connect();
            }, this.reconnectInterval);
        } else {
            console.error('达到最大重连次数，停止重连');
            this.showNotification('连接失败，请刷新页面', 'error');
        }
    }

    setupEventHandlers() {
        // 页面卸载时关闭连接
        window.addEventListener('beforeunload', () => {
            if (this.socket) {
                this.socket.close();
            }
        });

        // 心跳检测
        setInterval(() => {
            if (this.isConnected && this.socket) {
                this.socket.send(JSON.stringify({
                    type: 'ping'
                }));
            }
        }, 30000); // 每30秒发送一次心跳
    }

    send(message) {
        if (this.isConnected && this.socket) {
            this.socket.send(JSON.stringify(message));
        } else {
            console.error('WebSocket未连接');
        }
    }
}

// WebSocket客户端类定义完成，将通过layout.html中的代码进行初始化
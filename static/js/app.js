// Global variables
let currentUser = null;
let authToken = null;
let portfolioChart = null;
let tradingViewWidget = null;

// API base URL
const API_BASE_URL = '/api';

// Initialize application
document.addEventListener('DOMContentLoaded', function() {
    // Check if user is already logged in
    const savedToken = localStorage.getItem('authToken');
    if (savedToken) {
        authToken = savedToken;
        // Verify token and load dashboard
        verifyTokenAndLoadDashboard();
    }
    
    // Setup event listeners
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Login form
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    
    // Strategy form
    document.getElementById('strategyForm').addEventListener('submit', handleCreateStrategy);
    
    // API form
    document.getElementById('apiForm').addEventListener('submit', handleSaveAPISettings);
    
    // Risk form
    document.getElementById('riskForm').addEventListener('submit', handleSaveRiskSettings);
}

// Handle login
async function handleLogin(event) {
    event.preventDefault();
    
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    try {
        showLoading();
        
        const formData = new FormData();
        formData.append('username', username);
        formData.append('password', password);
        
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            const data = await response.json();
            authToken = data.access_token;
            currentUser = {
                id: data.user_id,
                username: data.username,
                email: data.email,
                is_admin: data.is_admin
            };
            
            // Save token to localStorage
            localStorage.setItem('authToken', authToken);
            
            // Show dashboard
            showDashboard();
            
            // Load initial data
            loadDashboardData();
        } else {
            const errorData = await response.json();
            showAlert('Login failed: ' + errorData.detail, 'danger');
        }
    } catch (error) {
        showAlert('Login error: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Verify token and load dashboard
async function verifyTokenAndLoadDashboard() {
    try {
        const response = await fetch(`${API_BASE_URL}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const userData = await response.json();
            currentUser = userData;
            showDashboard();
            loadDashboardData();
        } else {
            // Token invalid, clear and show login
            localStorage.removeItem('authToken');
            authToken = null;
            currentUser = null;
        }
    } catch (error) {
        console.error('Token verification error:', error);
        localStorage.removeItem('authToken');
        authToken = null;
        currentUser = null;
    }
}

// Show dashboard
function showDashboard() {
    document.getElementById('loginScreen').classList.add('hidden');
    document.getElementById('dashboard').classList.remove('hidden');
    document.getElementById('userDisplayName').textContent = currentUser.username;
}

// Show login screen
function showLoginScreen() {
    document.getElementById('dashboard').classList.add('hidden');
    document.getElementById('loginScreen').classList.remove('hidden');
}

// Logout
function logout() {
    authToken = null;
    currentUser = null;
    localStorage.removeItem('authToken');
    showLoginScreen();
}

// Show section
function showSection(sectionName) {
    // Hide all sections
    document.querySelectorAll('.section').forEach(section => {
        section.classList.add('hidden');
    });
    
    // Show selected section
    document.getElementById(sectionName + 'Section').classList.remove('hidden');
    
    // Update active nav link
    document.querySelectorAll('.sidebar .nav-link').forEach(link => {
        link.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // Load section-specific data
    switch(sectionName) {
        case 'overview':
            loadDashboardData();
            break;
        case 'trading':
            loadTradingData();
            break;
        case 'portfolio':
            loadPortfolioData();
            break;
        case 'strategies':
            loadStrategiesData();
            break;
        case 'history':
            loadHistoryData();
            break;
        case 'settings':
            loadSettingsData();
            break;
    }
}

// Load dashboard data
async function loadDashboardData() {
    try {
        showLoading();
        
        // Load portfolio overview
        const portfolioResponse = await fetch(`${API_BASE_URL}/portfolio/overview`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (portfolioResponse.ok) {
            const portfolioData = await portfolioResponse.json();
            updateDashboardStats(portfolioData);
            updatePortfolioChart(portfolioData);
            updateRecentTrades(portfolioData.recent_trades);
        }
        
        // Load bot status
        const botResponse = await fetch(`${API_BASE_URL}/trading/status`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (botResponse.ok) {
            const botData = await botResponse.json();
            updateBotStatus(botData);
        }
        
        // Load trading signals
        const signalsResponse = await fetch(`${API_BASE_URL}/trading/signals`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (signalsResponse.ok) {
            const signalsData = await signalsResponse.json();
            updateTradingSignals(signalsData.signals);
        }
        
    } catch (error) {
        showAlert('Error loading dashboard data: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Update dashboard stats
function updateDashboardStats(portfolioData) {
    const summary = portfolioData.portfolio_summary;
    
    document.getElementById('totalValue').textContent = formatCurrency(summary.total_value);
    document.getElementById('totalPnL').textContent = formatCurrency(summary.total_pnl);
    document.getElementById('activeStrategies').textContent = summary.total_positions;
    
    // Color code P&L
    const pnlElement = document.getElementById('totalPnL');
    if (summary.total_pnl > 0) {
        pnlElement.style.color = '#28a745';
    } else if (summary.total_pnl < 0) {
        pnlElement.style.color = '#dc3545';
    }
}

// Update portfolio chart
function updatePortfolioChart(portfolioData) {
    const ctx = document.getElementById('portfolioChart').getContext('2d');
    
    if (portfolioChart) {
        portfolioChart.destroy();
    }
    
    const labels = portfolioData.position_distribution.map(pos => pos.symbol);
    const data = portfolioData.position_distribution.map(pos => pos.total_value);
    const colors = generateColors(labels.length);
    
    portfolioChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Update recent trades
function updateRecentTrades(trades) {
    const container = document.getElementById('recentTrades');
    
    if (!trades || trades.length === 0) {
        container.innerHTML = '<p class="text-muted">No recent trades</p>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table table-sm">';
    html += '<thead><tr><th>Symbol</th><th>Side</th><th>Price</th><th>Value</th><th>Time</th></tr></thead><tbody>';
    
    trades.forEach(trade => {
        const sideClass = trade.side === 'BUY' ? 'text-success' : 'text-danger';
        const sideIcon = trade.side === 'BUY' ? '↑' : '↓';
        
        html += `<tr>
            <td><strong>${trade.symbol}</strong></td>
            <td><span class="${sideClass}">${sideIcon} ${trade.side}</span></td>
            <td>$${parseFloat(trade.price).toFixed(2)}</td>
            <td>$${parseFloat(trade.total_value).toFixed(2)}</td>
            <td><small>${new Date(trade.timestamp).toLocaleString()}</small></td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Update trading signals
function updateTradingSignals(signals) {
    const container = document.getElementById('tradingSignals');
    
    if (!signals || signals.length === 0) {
        container.innerHTML = '<p class="text-muted">No active signals</p>';
        return;
    }
    
    let html = '';
    signals.forEach(signal => {
        const signalClass = signal.signal_type === 'BUY' ? 'success' : 'danger';
        const signalIcon = signal.signal_type === 'BUY' ? '↑' : '↓';
        
        html += `<div class="alert alert-${signalClass} alert-sm">
            <strong>${signal.symbol}</strong> - ${signal.signal_type} ${signalIcon}<br>
            <small>Confidence: ${(signal.confidence * 100).toFixed(1)}% | Price: $${signal.price.toFixed(2)}</small>
        </div>`;
    });
    
    container.innerHTML = html;
}

// Update bot status
function updateBotStatus(botData) {
    const statusElement = document.getElementById('botStatus');
    const statusDisplay = document.getElementById('botStatusDisplay');
    
    const status = botData.status || 'stopped';
    statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    statusDisplay.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    
    // Color code status
    if (status === 'running') {
        statusElement.style.color = '#28a745';
        statusDisplay.className = 'text-success';
    } else if (status === 'paused') {
        statusElement.style.color = '#ffc107';
        statusDisplay.className = 'text-warning';
    } else {
        statusElement.style.color = '#dc3545';
        statusDisplay.className = 'text-danger';
    }
}

// Load trading data
async function loadTradingData() {
    try {
        showLoading();
        
        // Load bot status
        const botResponse = await fetch(`${API_BASE_URL}/trading/status`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (botResponse.ok) {
            const botData = await botResponse.json();
            updateBotStatus(botData);
        }
        
        // Initialize TradingView chart
        initTradingViewChart();
        
        // Load active strategies
        const strategiesResponse = await fetch(`${API_BASE_URL}/trading/strategies/user`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (strategiesResponse.ok) {
            const strategiesData = await strategiesResponse.json();
            updateActiveStrategies(strategiesData.strategies);
        }
        
    } catch (error) {
        showAlert('Error loading trading data: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Initialize TradingView chart
function initTradingViewChart() {
    if (tradingViewWidget) {
        tradingViewWidget.remove();
    }
    
    tradingViewWidget = new TradingView.widget({
        "width": "100%",
        "height": "100%",
        "symbol": "BINANCE:BTCUSDT",
        "interval": "1",
        "timezone": "Etc/UTC",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "container_id": "tradingViewChart"
    });
}

// Update active strategies
function updateActiveStrategies(strategies) {
    const container = document.getElementById('activeStrategiesList');
    
    if (!strategies || strategies.length === 0) {
        container.innerHTML = '<p class="text-muted">No active strategies</p>';
        return;
    }
    
    let html = '<div class="row">';
    strategies.forEach(strategy => {
        const statusClass = strategy.is_active ? 'active' : 'inactive';
        const statusBadge = strategy.is_active ? 
            '<span class="badge bg-success">Active</span>' : 
            '<span class="badge bg-secondary">Inactive</span>';
        
        html += `<div class="col-md-6 mb-3">
            <div class="card strategy-card ${statusClass}">
                <div class="card-body">
                    <h6 class="card-title">${strategy.name}</h6>
                    <p class="card-text">
                        <strong>Type:</strong> ${strategy.strategy_type}<br>
                        <strong>Symbol:</strong> ${strategy.symbol}<br>
                        <strong>Risk:</strong> <span class="badge bg-${getRiskColor(strategy.risk_level)}">${strategy.risk_level}</span>
                    </p>
                    ${statusBadge}
                    <div class="mt-2">
                        <button class="btn btn-sm btn-outline-primary" onclick="editStrategy(${strategy.id})">Edit</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteStrategy(${strategy.id})">Delete</button>
                    </div>
                </div>
            </div>
        </div>`;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

// Load portfolio data
async function loadPortfolioData() {
    try {
        showLoading();
        
        // Load portfolio overview
        const portfolioResponse = await fetch(`${API_BASE_URL}/portfolio/overview`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (portfolioResponse.ok) {
            const portfolioData = await portfolioResponse.json();
            updatePortfolioSummary(portfolioData);
            updatePositionsTable(portfolioData.position_distribution);
        }
        
    } catch (error) {
        showAlert('Error loading portfolio data: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Update portfolio summary
function updatePortfolioSummary(portfolioData) {
    const container = document.getElementById('portfolioSummary');
    const summary = portfolioData.portfolio_summary;
    
    let html = '<div class="row">';
    html += `<div class="col-md-6">
        <h6>Portfolio Summary</h6>
        <p><strong>Total Value:</strong> ${formatCurrency(summary.total_value)}</p>
        <p><strong>Total P&L:</strong> <span class="${summary.total_pnl >= 0 ? 'text-success' : 'text-danger'}">${formatCurrency(summary.total_pnl)}</p>
        <p><strong>Total Positions:</strong> ${summary.total_positions}</p>
    </div>`;
    
    html += `<div class="col-md-6">
        <h6>Risk Metrics</h6>
        <p><strong>Max Drawdown:</strong> ${(portfolioData.risk_metrics.max_drawdown * 100).toFixed(2)}%</p>
        <p><strong>Sharpe Ratio:</strong> ${portfolioData.risk_metrics.sharpe_ratio.toFixed(2)}</p>
        <p><strong>Volatility:</strong> ${(portfolioData.risk_metrics.volatility * 100).toFixed(2)}%</p>
    </div>`;
    
    html += '</div>';
    container.innerHTML = html;
}

// Update positions table
function updatePositionsTable(positions) {
    const container = document.getElementById('positionsTable');
    
    if (!positions || positions.length === 0) {
        container.innerHTML = '<p class="text-muted">No positions found</p>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table">';
    html += '<thead><tr><th>Symbol</th><th>Quantity</th><th>Avg Price</th><th>Current Price</th><th>Total Value</th><th>P&L</th><th>% of Portfolio</th></tr></thead><tbody>';
    
    positions.forEach(position => {
        const pnlClass = position.pnl >= 0 ? 'text-success' : 'text-danger';
        
        html += `<tr>
            <td><strong>${position.symbol}</strong></td>
            <td>${position.quantity.toFixed(6)}</td>
            <td>$${position.average_price.toFixed(2)}</td>
            <td>$${position.current_price.toFixed(2)}</td>
            <td>${formatCurrency(position.total_value)}</td>
            <td class="${pnlClass}">${formatCurrency(position.pnl)} (${position.pnl_percentage.toFixed(2)}%)</td>
            <td>${position.percentage_of_portfolio.toFixed(2)}%</td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Load strategies data
async function loadStrategiesData() {
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/trading/strategies/user`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const strategiesData = await response.json();
            updateStrategiesList(strategiesData.strategies);
        }
        
    } catch (error) {
        showAlert('Error loading strategies: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Update strategies list
function updateStrategiesList(strategies) {
    const container = document.getElementById('strategiesList');
    
    if (!strategies || strategies.length === 0) {
        container.innerHTML = '<p class="text-muted">No strategies found</p>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table">';
    html += '<thead><tr><th>Name</th><th>Type</th><th>Symbol</th><th>Risk Level</th><th>Status</th><th>Actions</th></tr></thead><tbody>';
    
    strategies.forEach(strategy => {
        const statusBadge = strategy.is_active ? 
            '<span class="badge bg-success">Active</span>' : 
            '<span class="badge bg-secondary">Inactive</span>';
        
        html += `<tr>
            <td>${strategy.name}</td>
            <td>${strategy.strategy_type}</td>
            <td>${strategy.symbol}</td>
            <td><span class="badge bg-${getRiskColor(strategy.risk_level)}">${strategy.risk_level}</span></td>
            <td>${statusBadge}</td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="editStrategy(${strategy.id})">Edit</button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteStrategy(${strategy.id})">Delete</button>
            </td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Handle create strategy
async function handleCreateStrategy(event) {
    event.preventDefault();
    
    const formData = {
        name: document.getElementById('strategyName').value,
        strategy_type: document.getElementById('strategyType').value,
        symbol: document.getElementById('tradingSymbol').value,
        risk_level: document.getElementById('riskLevel').value,
        parameters: {}
    };
    
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/trading/strategies/create`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        if (response.ok) {
            showAlert('Strategy created successfully!', 'success');
            document.getElementById('strategyForm').reset();
            loadStrategiesData();
        } else {
            const errorData = await response.json();
            showAlert('Error creating strategy: ' + errorData.detail, 'danger');
        }
    } catch (error) {
        showAlert('Error creating strategy: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Load history data
async function loadHistoryData() {
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/history/trades`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const historyData = await response.json();
            updateHistoryTable(historyData.trades);
        }
        
    } catch (error) {
        showAlert('Error loading history: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Load trading history with filters
async function loadTradingHistory() {
    try {
        showLoading();
        
        const symbol = document.getElementById('historySymbol').value;
        const side = document.getElementById('historySide').value;
        const startDate = document.getElementById('startDate').value;
        const endDate = document.getElementById('endDate').value;
        
        let url = `${API_BASE_URL}/history/trades?`;
        if (symbol) url += `symbol=${symbol}&`;
        if (side) url += `side=${side}&`;
        if (startDate) url += `start_date=${startDate}&`;
        if (endDate) url += `end_date=${endDate}&`;
        
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const historyData = await response.json();
            updateHistoryTable(historyData.trades);
        }
        
    } catch (error) {
        showAlert('Error loading trading history: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Update history table
function updateHistoryTable(trades) {
    const container = document.getElementById('historyTable');
    
    if (!trades || trades.length === 0) {
        container.innerHTML = '<p class="text-muted">No trades found</p>';
        return;
    }
    
    let html = '<div class="table-responsive"><table class="table">';
    html += '<thead><tr><th>Date</th><th>Symbol</th><th>Side</th><th>Quantity</th><th>Price</th><th>Value</th><th>Strategy</th></tr></thead><tbody>';
    
    trades.forEach(trade => {
        const sideClass = trade.side === 'BUY' ? 'text-success' : 'text-danger';
        const sideIcon = trade.side === 'BUY' ? '↑' : '↓';
        
        html += `<tr>
            <td><small>${new Date(trade.timestamp).toLocaleString()}</small></td>
            <td><strong>${trade.symbol}</strong></td>
            <td><span class="${sideClass}">${sideIcon} ${trade.side}</span></td>
            <td>${trade.quantity.toFixed(6)}</td>
            <td>$${parseFloat(trade.price).toFixed(2)}</td>
            <td>${formatCurrency(trade.total_value)}</td>
            <td>${trade.strategy || 'Manual'}</td>
        </tr>`;
    });
    
    html += '</tbody></table></div>';
    container.innerHTML = html;
}

// Load settings data
async function loadSettingsData() {
    // Load current settings from localStorage or API
    const savedSettings = localStorage.getItem('botSettings');
    if (savedSettings) {
        const settings = JSON.parse(savedSettings);
        document.getElementById('binanceApiKey').value = settings.binanceApiKey || '';
        document.getElementById('binanceSecretKey').value = settings.binanceSecretKey || '';
        document.getElementById('exchangeName').value = settings.exchangeName || 'binance';
        document.getElementById('testnetMode').checked = settings.testnetMode !== false;
    }
    
    const savedRiskSettings = localStorage.getItem('riskSettings');
    if (savedRiskSettings) {
        const riskSettings = JSON.parse(savedRiskSettings);
        document.getElementById('maxPositionSize').value = riskSettings.maxPositionSize || 10;
        document.getElementById('stopLossPercentage').value = riskSettings.stopLossPercentage || 2;
        document.getElementById('takeProfitPercentage').value = riskSettings.takeProfitPercentage || 6;
        document.getElementById('maxDailyLoss').value = riskSettings.maxDailyLoss || 5;
    }
}

// Handle save API settings
function handleSaveAPISettings(event) {
    event.preventDefault();
    
    const settings = {
        binanceApiKey: document.getElementById('binanceApiKey').value,
        binanceSecretKey: document.getElementById('binanceSecretKey').value,
        exchangeName: document.getElementById('exchangeName').value,
        testnetMode: document.getElementById('testnetMode').checked
    };
    
    localStorage.setItem('botSettings', JSON.stringify(settings));
    showAlert('API settings saved successfully!', 'success');
}

// Handle save risk settings
function handleSaveRiskSettings(event) {
    event.preventDefault();
    
    const riskSettings = {
        maxPositionSize: parseFloat(document.getElementById('maxPositionSize').value),
        stopLossPercentage: parseFloat(document.getElementById('stopLossPercentage').value),
        takeProfitPercentage: parseFloat(document.getElementById('takeProfitPercentage').value),
        maxDailyLoss: parseFloat(document.getElementById('maxDailyLoss').value)
    };
    
    localStorage.setItem('riskSettings', JSON.stringify(riskSettings));
    showAlert('Risk settings saved successfully!', 'success');
}

// Bot control functions
async function startBot() {
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/trading/start`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                strategy_ids: [1], // Default strategy ID
                exchange_name: 'binance'
            })
        });
        
        if (response.ok) {
            showAlert('Bot started successfully!', 'success');
            loadTradingData();
        } else {
            const errorData = await response.json();
            showAlert('Error starting bot: ' + errorData.detail, 'danger');
        }
    } catch (error) {
        showAlert('Error starting bot: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

async function pauseBot() {
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/trading/pause`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            showAlert('Bot paused successfully!', 'success');
            loadTradingData();
        } else {
            const errorData = await response.json();
            showAlert('Error pausing bot: ' + errorData.detail, 'danger');
        }
    } catch (error) {
        showAlert('Error pausing bot: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

async function stopBot() {
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/trading/stop`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            showAlert('Bot stopped successfully!', 'success');
            loadTradingData();
        } else {
            const errorData = await response.json();
            showAlert('Error stopping bot: ' + errorData.detail, 'danger');
        }
    } catch (error) {
        showAlert('Error stopping bot: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

// Utility functions
function showLoading() {
    document.getElementById('loading').style.display = 'block';
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    // Insert at the top of the main content
    const mainContent = document.querySelector('.main-content');
    mainContent.insertBefore(alertDiv, mainContent.firstChild);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

function generateColors(count) {
    const colors = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF',
        '#FF9F40', '#FF6384', '#C9CBCF', '#4BC0C0', '#FF6384'
    ];
    
    const result = [];
    for (let i = 0; i < count; i++) {
        result.push(colors[i % colors.length]);
    }
    return result;
}

function getRiskColor(riskLevel) {
    switch (riskLevel.toLowerCase()) {
        case 'low': return 'success';
        case 'medium': return 'warning';
        case 'high': return 'danger';
        default: return 'secondary';
    }
}

// Edit strategy function
function editStrategy(strategyId) {
    // Implementation for editing strategy
    showAlert('Edit strategy functionality coming soon!', 'info');
}

// Delete strategy function
async function deleteStrategy(strategyId) {
    if (!confirm('Are you sure you want to delete this strategy?')) {
        return;
    }
    
    try {
        showLoading();
        
        const response = await fetch(`${API_BASE_URL}/trading/strategies/${strategyId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            showAlert('Strategy deleted successfully!', 'success');
            loadStrategiesData();
        } else {
            const errorData = await response.json();
            showAlert('Error deleting strategy: ' + errorData.detail, 'danger');
        }
    } catch (error) {
        showAlert('Error deleting strategy: ' + error.message, 'danger');
    } finally {
        hideLoading();
    }
}

/**
 * 合浦珠还 - 失物招领平台前端逻辑
 */

// 全局状态
const state = {
    currentPage: 'welcome',
    user: null,
    token: localStorage.getItem('token'),
    lostPage: 1,
    foundPage: 1
};

// API 基础URL
const API_BASE = '';

// ============ 工具函数 ============

function showToast(message, duration = 3000) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, duration);
}

async function apiRequest(url, options = {}) {
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }
    
    try {
        const response = await fetch(API_BASE + url, {
            ...options,
            headers
        });
        
        const data = await response.json();
        
        if (data.code === 401) {
            state.token = null;
            localStorage.removeItem('token');
            showToast('请先登录');
            showAuthModal();
            return null;
        }
        
        return data;
    } catch (error) {
        console.error('API Error:', error);
        showToast('网络错误，请重试');
        return null;
    }
}

// ============ 页面导航 ============

function showPage(pageId) {
    // 隐藏所有页面
    document.querySelectorAll('.page').forEach(page => {
        page.style.display = 'none';
    });
    
    // 显示目标页面
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.style.display = 'block';
    }
    
    // 更新导航状态
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // 更新当前页面
    state.currentPage = pageId;
    
    // 加载页面数据
    switch(pageId) {
        case 'welcome':
            loadLostList();
            loadFoundList();
            break;
        case 'search':
            document.getElementById('searchInput').focus();
            break;
        case 'matches':
            loadMatches();
            break;
        case 'user-center':
            loadUserProfile();
            break;
    }
}

// ============ 认证相关 ============

function showAuthModal() {
    document.getElementById('authModal').style.display = 'flex';
    showLogin();
}

function showLogin() {
    document.getElementById('authTitle').textContent = '登录';
    document.getElementById('loginForm').style.display = 'block';
    document.getElementById('registerForm').style.display = 'none';
}

function showRegister() {
    document.getElementById('authTitle').textContent = '注册';
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('registerForm').style.display = 'block';
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

// 登录
document.getElementById('loginForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        username: formData.get('username'),
        password: formData.get('password')
    };
    
    const result = await apiRequest('/api/login', {
        method: 'POST',
        body: JSON.stringify(data)
    });
    
    if (result && result.code === 200) {
        state.token = result.data.token;
        state.user = result.data;
        localStorage.setItem('token', state.token);
        localStorage.setItem('user', JSON.stringify(result.data));
        
        closeModal('authModal');
        showToast('登录成功');
        updateUserUI();
    } else if (result) {
        showToast(result.msg);
    }
});

// 注册
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const data = {
        username: formData.get('username'),
        password: formData.get('password'),
        phone: formData.get('phone'),
        student_id: formData.get('student_id')
    };
    
    const result = await apiRequest('/api/register', {
        method: 'POST',
        body: JSON.stringify(data)
    });
    
    if (result && result.code === 200) {
        showToast('注册成功，请登录');
        showLogin();
    } else if (result) {
        showToast(result.msg);
    }
});

// 更新用户UI
function updateUserUI() {
    const userInfo = document.getElementById('userInfo');
    if (state.user) {
        userInfo.innerHTML = `
            <div class="user-card">
                <div class="user-avatar">
                    <i class="fas fa-user"></i>
                </div>
                <h3>${state.user.username}</h3>
                <div class="user-stats">
                    <div class="stat-item">
                        <div class="num" id="lostCount">0</div>
                        <div class="label">失物</div>
                    </div>
                    <div class="stat-item">
                        <div class="num" id="foundCount">0</div>
                        <div class="label">拾物</div>
                    </div>
                    <div class="stat-item">
                        <div class="num" id="matchCount">0</div>
                        <div class="label">匹配</div>
                    </div>
                </div>
            </div>
        `;
    }
}

// ============ 数据加载 ============

async function loadLostList() {
    const result = await apiRequest(`/api/lost/list?page=${state.lostPage}&per_page=5`);
    
    if (result && result.code === 200) {
        const container = document.getElementById('lostList');
        
        if (result.data.items.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>暂无失物信息</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = result.data.items.map(item => `
            <div class="item-card" onclick="showDetail('lost', ${item.id})">
                <div class="item-image">
                    ${item.image_url 
                        ? `<img src="${item.image_url}" alt="${item.title}">` 
                        : '<i class="fas fa-image"></i>'}
                </div>
                <div class="item-info">
                    <h4>${item.title}</h4>
                    <p>${item.description}</p>
                    <div class="item-meta">
                        <span><i class="fas fa-map-marker-alt"></i> ${item.location || '未知'}</span>
                        <span><i class="fas fa-clock"></i> ${item.created_at}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }
}

async function loadFoundList() {
    const result = await apiRequest(`/api/found/list?page=${state.foundPage}&per_page=5`);
    
    if (result && result.code === 200) {
        const container = document.getElementById('foundList');
        
        if (result.data.items.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>暂无拾物信息</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = result.data.items.map(item => `
            <div class="item-card" onclick="showDetail('found', ${item.id})">
                <div class="item-image">
                    ${item.image_url 
                        ? `<img src="${item.image_url}" alt="${item.title}">` 
                        : '<i class="fas fa-image"></i>'}
                </div>
                <div class="item-info">
                    <h4>${item.title}</h4>
                    <p>${item.description}</p>
                    <div class="item-meta">
                        <span><i class="fas fa-map-marker-alt"></i> ${item.location || '未知'}</span>
                        <span><i class="fas fa-clock"></i> ${item.created_at}</span>
                    </div>
                </div>
            </div>
        `).join('');
    }
}

async function loadMoreLost() {
    state.lostPage++;
    await loadLostList();
}

async function loadMoreFound() {
    state.foundPage++;
    await loadFoundList();
}

// ============ 详情页 ============

async function showDetail(type, id) {
    const result = await apiRequest(`/api/${type}/${id}`);
    
    if (result && result.code === 200) {
        const item = result.data;
        const container = document.getElementById('detailContent');
        
        container.innerHTML = `
            <div class="detail-card">
                ${item.image_url 
                    ? `<img src="${item.image_url}" class="detail-image" alt="${item.title}">` 
                    : '<div class="detail-image" style="display:flex;align-items:center;justify-content:center;"><i class="fas fa-image" style="font-size:48px;color:var(--border-color)"></i></div>'}
                <div class="detail-info">
                    <h2>${item.title}</h2>
                    <div class="detail-meta">
                        <p><i class="fas fa-tag"></i> ${item.category}</p>
                        <p><i class="fas fa-map-marker-alt"></i> ${item.location || '未知'}</p>
                        <p><i class="fas fa-clock"></i> ${type === 'lost' ? '丢失' : '拾取'}时间：${item.lost_time || item.found_time || '未知'}</p>
                        <p><i class="fas fa-user"></i> 发布者：${item.user.username}</p>
                        <p><i class="fas fa-calendar"></i> 发布于：${item.created_at}</p>
                    </div>
                    <div class="detail-description">
                        <h4>详细描述</h4>
                        <p>${item.description}</p>
                    </div>
                    ${item.contact ? `
                        <div class="detail-contact">
                            <i class="fas fa-phone"></i>
                            <div>
                                <strong>联系方式</strong>
                                <p>${item.contact}</p>
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
        
        showPage('detail');
    }
}

// ============ 发布功能 ============

// 上传区域点击
document.querySelectorAll('.upload-area').forEach(area => {
    area.addEventListener('click', () => {
        area.querySelector('input[type="file"]').click();
    });
});

// 文件选择预览
document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const preview = input.closest('.form-group').querySelector('.image-preview');
                preview.innerHTML = `<img src="${e.target.result}" alt="预览">`;
            };
            reader.readAsDataURL(file);
        }
    });
});

// 发布失物
document.getElementById('lostForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!state.token) {
        showAuthModal();
        return;
    }
    
    const formData = new FormData(e.target);
    
    const result = await fetch(API_BASE + '/api/lost', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${state.token}`
        },
        body: formData
    }).then(res => res.json());
    
    if (result.code === 200) {
        showToast('发布成功');
        e.target.reset();
        document.getElementById('lostPreview').innerHTML = '';
        showPage('welcome');
    } else {
        showToast(result.msg || '发布失败');
    }
});

// 发布拾物
document.getElementById('foundForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    if (!state.token) {
        showAuthModal();
        return;
    }
    
    const formData = new FormData(e.target);
    
    const result = await fetch(API_BASE + '/api/found', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${state.token}`
        },
        body: formData
    }).then(res => res.json());
    
    if (result.code === 200) {
        showToast('发布成功');
        e.target.reset();
        document.getElementById('foundPreview').innerHTML = '';
        showPage('welcome');
    } else {
        showToast(result.msg || '发布失败');
    }
});

// ============ 搜索功能 ============

async function doSearch() {
    const keyword = document.getElementById('searchInput').value.trim();
    
    if (!keyword) {
        showToast('请输入搜索关键词');
        return;
    }
    
    const result = await apiRequest(`/api/search?q=${encodeURIComponent(keyword)}`);
    
    if (result && result.code === 200) {
        const container = document.getElementById('searchResults');
        const { lost, found } = result.data;
        
        if (lost.length === 0 && found.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-search"></i>
                    <p>未找到相关物品</p>
                </div>
            `;
            return;
        }
        
        let html = '';
        
        if (lost.length > 0) {
            html += '<h3 style="margin: 15px 0 10px;"><i class="fas fa-exclamation-circle" style="color:var(--danger-color)"></i> 失物</h3>';
            html += lost.map(item => `
                <div class="item-card" onclick="showDetail('lost', ${item.id})">
                    <div class="item-image">
                        ${item.image_url 
                            ? `<img src="${item.image_url}" alt="${item.title}">` 
                            : '<i class="fas fa-image"></i>'}
                    </div>
                    <div class="item-info">
                        <h4>${item.title}</h4>
                        <p>${item.description}</p>
                        <div class="item-meta">
                            <span><i class="fas fa-map-marker-alt"></i> ${item.location || '未知'}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        if (found.length > 0) {
            html += '<h3 style="margin: 15px 0 10px;"><i class="fas fa-hand-holding-heart" style="color:var(--success-color)"></i> 拾物</h3>';
            html += found.map(item => `
                <div class="item-card" onclick="showDetail('found', ${item.id})">
                    <div class="item-image">
                        ${item.image_url 
                            ? `<img src="${item.image_url}" alt="${item.title}">` 
                            : '<i class="fas fa-image"></i>'}
                    </div>
                    <div class="item-info">
                        <h4>${item.title}</h4>
                        <p>${item.description}</p>
                        <div class="item-meta">
                            <span><i class="fas fa-map-marker-alt"></i> ${item.location || '未知'}</span>
                        </div>
                    </div>
                </div>
            `).join('');
        }
        
        container.innerHTML = html;
    }
}

// 回车搜索
document.getElementById('searchInput').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        doSearch();
    }
});

// ============ 匹配功能 ============

async function loadMatches() {
    if (!state.token) {
        showAuthModal();
        return;
    }
    
    const result = await apiRequest('/api/match/list');
    
    if (result && result.code === 200) {
        const container = document.getElementById('matchesList');
        
        if (result.data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-link"></i>
                    <p>暂无匹配记录</p>
                </div>
            `;
            return;
        }
        
        container.innerHTML = result.data.map(match => `
            <div class="match-card">
                <div class="match-header">
                    <span>匹配于 ${match.created_at}</span>
                    <span class="match-score">匹配度 ${Math.round(match.score * 100)}%</span>
                </div>
                <div class="match-items">
                    <div class="match-item">
                        <h4><i class="fas fa-exclamation-circle"></i> 失物</h4>
                        <p><strong>${match.lost_item.title}</strong></p>
                        <p>${match.lost_item.location}</p>
                    </div>
                    <div class="match-item">
                        <h4><i class="fas fa-hand-holding-heart"></i> 拾物</h4>
                        <p><strong>${match.found_item.title}</strong></p>
                        <p>${match.found_item.location}</p>
                    </div>
                </div>
                ${match.status === 'pending' ? `
                    <div class="match-actions">
                        <button class="confirm-btn" onclick="confirmMatch(${match.id})">
                            <i class="fas fa-check"></i> 确认匹配
                        </button>
                        <button class="reject-btn" onclick="rejectMatch(${match.id})">
                            <i class="fas fa-times"></i> 忽略
                        </button>
                    </div>
                ` : `
                    <div class="match-actions">
                        <span class="status-badge status-${match.status}">
                            ${match.status === 'confirmed' ? '已确认' : '已忽略'}
                        </span>
                    </div>
                `}
            </div>
        `).join('');
    }
}

async function confirmMatch(matchId) {
    const result = await apiRequest(`/api/match/${matchId}/confirm`, {
        method: 'POST'
    });
    
    if (result && result.code === 200) {
        showToast('匹配已确认');
        loadMatches();
    }
}

async function rejectMatch(matchId) {
    // 简单处理，直接刷新
    loadMatches();
}

// ============ 用户中心 ============

async function loadUserProfile() {
    if (!state.token) {
        showAuthModal();
        return;
    }
    
    const result = await apiRequest('/api/user/profile');
    
    if (result && result.code === 200) {
        state.user = result.data;
        updateUserUI();
        
        // 更新统计数据
        document.getElementById('lostCount').textContent = result.data.lost_count;
        document.getElementById('foundCount').textContent = result.data.found_count;
        document.getElementById('matchCount').textContent = result.data.match_count;
    }
    
    // 加载用户发布的物品
    const itemsResult = await apiRequest('/api/user/items');
    
    if (itemsResult && itemsResult.code === 200) {
        const container = document.getElementById('userItems');
        const { lost, found } = itemsResult.data;
        
        let html = '';
        
        if (lost.length > 0) {
            html += '<h3><i class="fas fa-exclamation-circle" style="color:var(--danger-color)"></i> 我的失物</h3>';
            html += lost.map(item => `
                <div class="user-item-card">
                    <div class="user-item-info">
                        <h4>${item.title}</h4>
                        <p>${item.created_at}</p>
                    </div>
                    <span class="status-badge status-${item.status}">
                        ${item.status === 'pending' ? '待匹配' : item.status === 'matched' ? '已匹配' : '已解决'}
                    </span>
                </div>
            `).join('');
        }
        
        if (found.length > 0) {
            html += '<h3 style="margin-top:20px"><i class="fas fa-hand-holding-heart" style="color:var(--success-color)"></i> 我的拾物</h3>';
            html += found.map(item => `
                <div class="user-item-card">
                    <div class="user-item-info">
                        <h4>${item.title}</h4>
                        <p>${item.created_at}</p>
                    </div>
                    <span class="status-badge status-${item.status}">
                        ${item.status === 'pending' ? '待匹配' : item.status === 'matched' ? '已匹配' : '已解决'}
                    </span>
                </div>
            `).join('');
        }
        
        if (!html) {
            html = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>暂无发布记录</p>
                </div>
            `;
        }
        
        container.innerHTML = html;
    }
}

// ============ 主题切换 ============

document.getElementById('themeToggle').addEventListener('click', () => {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    const icon = document.querySelector('#themeToggle i');
    icon.className = newTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
});

// ============ 初始化 ============

function init() {
    // 加载保存的主题
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const icon = document.querySelector('#themeToggle i');
    icon.className = savedTheme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    
    // 检查登录状态
    if (state.token) {
        const savedUser = localStorage.getItem('user');
        if (savedUser) {
            state.user = JSON.parse(savedUser);
            updateUserUI();
        }
    }
    
    // 加载首页数据
    loadLostList();
    loadFoundList();
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);

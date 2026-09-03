// Currency Configurations
const CURRENCIES = {
    USD: { symbol: '$', code: 'USD', name: 'US Dollar', rate: 1.0, flag: '🇺🇸' },
    EUR: { symbol: '€', code: 'EUR', name: 'Euro', rate: 0.87, flag: '🇪🇺' },
    GBP: { symbol: '£', code: 'GBP', name: 'British Pound', rate: 0.74, flag: '🇬🇧' },
    CAD: { symbol: 'CA$', code: 'CAD', name: 'Canadian Dollar', rate: 1.39, flag: '🇨🇦' },
    AUD: { symbol: 'AU$', code: 'AUD', name: 'Australian Dollar', rate: 1.40, flag: '🇦🇺' },
    INR: { symbol: '₹', code: 'INR', name: 'Indian Rupee', rate: 94.9, flag: '🇮🇳' },
    JPY: { symbol: '¥', code: 'JPY', name: 'Japanese Yen', rate: 160.0, flag: '🇯🇵' },
    NGN: { symbol: '₦', code: 'NGN', name: 'Nigerian Naira', rate: 1410.0, flag: '🇳🇬' },
    GHS: { symbol: 'GH₵', code: 'GHS', name: 'Ghanaian Cedi', rate: 11.27, flag: '🇬🇭' }
};

// Tech Stack Calculator Skills
const AVAILABLE_STACK_SKILLS = [
    { name: 'SQL', uplift: 8000, demand: 28.0, category: 'Database' },
    { name: 'Python', uplift: 14000, demand: 31.1, category: 'Programming' },
    { name: 'AWS', uplift: 21000, demand: 18.5, category: 'Cloud' },
    { name: 'Spark', uplift: 26000, demand: 12.4, category: 'Big Data' },
    { name: 'PyTorch', uplift: 32000, demand: 8.2, category: 'AI/ML' },
    { name: 'Snowflake', uplift: 22000, demand: 11.0, category: 'Database' },
    { name: 'Airflow', uplift: 19000, demand: 9.8, category: 'Data Eng' },
    { name: 'Docker', uplift: 16000, demand: 14.2, category: 'DevOps' },
    { name: 'Kubernetes', uplift: 28000, demand: 10.5, category: 'DevOps' },
    { name: 'Tableau', uplift: 9000, demand: 19.1, category: 'Analytics' }
];

// Dashboard State
const state = {
    role: 'All Roles',
    seniority: 'All Levels',
    country: 'All Countries',
    salaryMin: 0,
    remote: false,
    currency: 'USD',
    activeTab: 'demand',
    chartMetric: '%',
    jobsPage: 1,
    jobSearch: '',
    jobSort: 'date',
    customStack: ['SQL', 'Python', 'AWS'],
    rawKpis: null,
    rawRoiData: null,
    rawJobsRes: null,
    rawEmployersData: null,
    rawGapData: null
};

let demandChartInstance = null;
let categoryChartInstance = null;
let radarChartInstance = null;
let employersChartInstance = null;

// Toast Notification System
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const toast = document.createElement('div');
    toast.className = `pointer-events-auto bg-slate-900 border ${type === 'success' ? 'border-emerald-500 text-emerald-300' : 'border-blue-500 text-blue-300'} px-4 py-3 rounded-xl shadow-2xl text-xs font-semibold flex items-center space-x-2 transform translate-y-4 opacity-0 transition-all duration-300`;
    toast.innerHTML = `<i class="fa-solid ${type === 'success' ? 'fa-circle-check text-emerald-400' : 'fa-circle-info text-blue-400'} text-base"></i><span>${message}</span>`;

    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.remove('translate-y-4', 'opacity-0');
    }, 10);

    setTimeout(() => {
        toast.classList.add('opacity-0', 'translate-y-4');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Currency Helpers
function formatSalary(usdAmount, prefix = '', suffix = '') {
    if (usdAmount === null || usdAmount === undefined || isNaN(usdAmount) || usdAmount <= 0) {
        return 'Salary Undisclosed';
    }
    const curr = CURRENCIES[state.currency] || CURRENCIES.USD;
    const converted = usdAmount * curr.rate;
    const formatted = Math.round(converted).toLocaleString();
    return `${prefix}${curr.symbol}${formatted}${suffix}`;
}

function setCurrency(code) {
    if (!CURRENCIES[code]) return;
    state.currency = code;
    updateURL();
    syncUIWithState();
    reRenderAllSalaries();
    updateCurrencyConverterModal();
    renderCustomStackCalculator();
    showToast(`Currency updated to ${code} (${CURRENCIES[code].symbol})`, 'success');
}

function reRenderAllSalaries() {
    if (state.rawKpis) renderKPIs(state.rawKpis);
    if (state.rawRoiData) renderRoiMatrixData(state.rawRoiData);
    if (state.rawJobsRes) renderJobsFeedData(state.rawJobsRes);
    if (state.rawEmployersData) {
        renderEmployersData(state.rawEmployersData);
        renderEmployersChart(state.rawEmployersData);
    }
    if (state.rawGapData) renderGapAnalysisData(state.rawGapData);
}

async function loadCountriesDropdown() {
    const countries = await fetchAPI('/api/countries');
    if (!countries || !Array.isArray(countries) || countries.length === 0) return;
    const select = document.getElementById('countrySelect');
    if (!select) return;
    const currentVal = state.country;
    select.innerHTML = '<option value="All Countries">All Countries (160 Markets)</option>' +
        countries.map(c => `<option value="${c}">${c}</option>`).join('');
    select.value = currentVal;
}

window.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('role')) state.role = params.get('role');
    if (params.get('seniority')) state.seniority = params.get('seniority');
    if (params.get('country')) state.country = params.get('country');
    if (params.get('salaryMin')) state.salaryMin = parseInt(params.get('salaryMin')) || 0;
    if (params.get('remote')) state.remote = params.get('remote') === 'true';
    if (params.get('currency')) state.currency = params.get('currency');

    loadCountriesDropdown();
    syncUIWithState();
    refreshDashboard();
    renderCustomStackPills();
    renderCustomStackCalculator();
});

function syncUIWithState() {
    document.querySelectorAll('#roleChipContainer button').forEach(btn => {
        const r = btn.innerText.trim();
        btn.classList.toggle('active', (r === 'All Roles' && state.role === 'All Roles') || r.includes(state.role));
    });

    document.getElementById('senioritySelect').value = state.seniority;
    document.getElementById('countrySelect').value = state.country;
    document.getElementById('salaryMinSelect').value = state.salaryMin;
    document.getElementById('currencySelect').value = state.currency;

    const remoteBtn = document.getElementById('remoteToggleBtn');
    const remoteTxt = document.getElementById('remoteToggleText');
    if (state.remote) {
        remoteBtn.classList.add('border-emerald-500', 'bg-emerald-950/40', 'text-emerald-300');
        remoteTxt.innerText = 'Remote: ON';
    } else {
        remoteBtn.classList.remove('border-emerald-500', 'bg-emerald-950/40', 'text-emerald-300');
        remoteTxt.innerText = 'Remote: OFF';
    }

    const currSymbol = (CURRENCIES[state.currency] || CURRENCIES.USD).symbol;
    document.getElementById('activeFilterSummary').innerHTML =
        `<i class="fa-solid fa-sliders text-blue-400"></i> Filter Scope: <b>${state.role}</b> | <b>${state.seniority}</b> | <b>${state.country}</b> ${state.salaryMin > 0 ? `| <b class="text-emerald-400">&gt;$${state.salaryMin.toLocaleString()}</b>` : ''} ${state.remote ? '| <b class="text-emerald-400">Remote Only</b>' : ''} | <b class="text-amber-400">Currency: ${state.currency} (${currSymbol})</b>`;
}

function setFilter(type, val) {
    state[type] = val;
    updateURL();
    syncUIWithState();
    refreshDashboard();
}

function toggleRemoteFilter() {
    state.remote = !state.remote;
    updateURL();
    syncUIWithState();
    refreshDashboard();
}

function resetAllFilters() {
    state.role = 'All Roles';
    state.seniority = 'All Levels';
    state.country = 'All Countries';
    state.salaryMin = 0;
    state.currency = 'USD';
    state.remote = false;
    updateURL();
    syncUIWithState();
    refreshDashboard();
    showToast('All dashboard filters reset to default', 'info');
}

function updateURL() {
    const params = new URLSearchParams();
    if (state.role !== 'All Roles') params.set('role', state.role);
    if (state.seniority !== 'All Levels') params.set('seniority', state.seniority);
    if (state.country !== 'All Countries') params.set('country', state.country);
    if (state.salaryMin > 0) params.set('salaryMin', state.salaryMin);
    if (state.currency !== 'USD') params.set('currency', state.currency);
    if (state.remote) params.set('remote', 'true');

    const newUrl = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
    window.history.pushState({ path: newUrl }, '', newUrl);
}

function switchTab(tabId) {
    state.activeTab = tabId;
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active', 'text-blue-400'));
    document.querySelectorAll('.tab-content').forEach(c => c.classList.add('hidden'));

    document.getElementById(`tab-${tabId}`).classList.add('active', 'text-blue-400');
    document.getElementById(`content-${tabId}`).classList.remove('hidden');

    if (tabId === 'roi') loadRoiMatrix();
    if (tabId === 'jobs') loadJobsFeed();
    if (tabId === 'career') runGapAnalysis();
    if (tabId === 'employers') loadEmployers();
}

// API Utilities
async function fetchAPI(endpoint) {
    try {
        const res = await fetch(endpoint);
        if (!res.ok) {
            console.warn(`API response not OK (${res.status}) for ${endpoint}`);
            return null;
        }
        const data = await res.json();
        return data;
    } catch (err) {
        console.error("API fetch error:", err);
        return null;
    }
}

// System Diagnostics
function openDiagnosticsModal() {
    document.getElementById('diagnosticsOverlay').classList.remove('hidden');
    document.getElementById('diagnosticsModal').classList.remove('hidden');
    runSystemDiagnosticPing();
}

function closeDiagnosticsModal() {
    document.getElementById('diagnosticsOverlay').classList.add('hidden');
    document.getElementById('diagnosticsModal').classList.add('hidden');
}

async function runSystemDiagnosticPing() {
    const pingEl = document.getElementById('diagLatencyVal');
    const statusEl = document.getElementById('diagDbStatus');
    const cacheEl = document.getElementById('diagCacheEntries');
    const timeEl = document.getElementById('diagTimestamp');
    const pingDot = document.getElementById('diagPingDot');

    if (pingEl) pingEl.innerText = 'Pinging...';
    if (pingDot) pingDot.className = 'w-3 h-3 rounded-full bg-amber-400 animate-ping';

    const t0 = performance.now();
    try {
        const res = await fetch('/api/health');
        const data = await res.json();
        const latency = (performance.now() - t0).toFixed(1);

        if (pingEl) {
            pingEl.innerHTML = `${latency} <span class="text-xs font-sans text-slate-400">ms</span>`;
        }
        if (statusEl) {
            statusEl.innerText = data.database_status === 'online' ? 'Online (Connected)' : 'Offline / Standby';
            statusEl.className = data.database_status === 'online' ? 'font-mono font-bold text-emerald-400' : 'font-mono font-bold text-rose-400';
        }
        if (cacheEl) {
            cacheEl.innerText = `${data.cache_entries || 0} active keys`;
        }
        if (timeEl) {
            timeEl.innerText = data.timestamp || new Date().toISOString();
        }
        if (pingDot) {
            pingDot.className = 'w-3 h-3 rounded-full bg-emerald-400 animate-pulse';
        }
    } catch (err) {
        if (pingEl) pingEl.innerText = 'Timeout / Error';
        if (statusEl) {
            statusEl.innerText = 'Offline';
            statusEl.className = 'font-mono font-bold text-rose-400';
        }
        if (pingDot) pingDot.className = 'w-3 h-3 rounded-full bg-rose-500';
    }
}

// KPI Rendering
function renderKPIs(kpis) {
    if (!kpis) return;
    document.getElementById('kpiTotalJobs').innerText = (kpis.total_postings || 0).toLocaleString();
    document.getElementById('headerJobCount').innerText = `${(kpis.total_postings || 0).toLocaleString()} Postings`;

    document.getElementById('kpiMedianSalary').innerText = formatSalary(kpis.median_salary);
    document.getElementById('kpiP25Salary').innerText = formatSalary(kpis.p25_salary);
    document.getElementById('kpiP75Salary').innerText = formatSalary(kpis.p75_salary);

    document.getElementById('kpiTopSkill').innerText = kpis.top_skill || 'Python';
    document.getElementById('kpiTopSkillPct').innerText = `${kpis.top_skill_pct || 0}%`;
    document.getElementById('kpiTopCombo').innerText = kpis.top_combo || 'Python + AWS + PyTorch';

    const upliftRaw = kpis.top_combo_uplift_usd || 34200;
    document.getElementById('kpiComboUplift').innerText = `${formatSalary(upliftRaw, '+')}/yr Salary Boost`;
    const share = (((kpis.total_postings || 0) / 767235) * 100);
    const shareStr = share >= 1 ? `${share.toFixed(1)}% of Market` : (share > 0 ? `${share.toFixed(2)}% of Market` : `0.0% of Market`);
    document.getElementById('kpiJobShare').innerText = shareStr;
}

// Default Skill Catalog
function getClientFallbackSkills(role) {
    const catalog = {
        'Data Engineer': [
            { skill_name: 'SQL', skill_type: 'programming', demand_count: 137993, pct_of_total_postings: 60.99 },
            { skill_name: 'Python', skill_type: 'programming', demand_count: 133559, pct_of_total_postings: 59.03 },
            { skill_name: 'AWS', skill_type: 'cloud', demand_count: 67200, pct_of_total_postings: 29.70 },
            { skill_name: 'Spark', skill_type: 'libraries', demand_count: 48900, pct_of_total_postings: 21.61 },
            { skill_name: 'Snowflake', skill_type: 'databases', demand_count: 41200, pct_of_total_postings: 18.21 },
            { skill_name: 'Azure', skill_type: 'cloud', demand_count: 39500, pct_of_total_postings: 17.46 },
            { skill_name: 'Java', skill_type: 'programming', demand_count: 38200, pct_of_total_postings: 16.88 },
            { skill_name: 'Airflow', skill_type: 'libraries', demand_count: 26400, pct_of_total_postings: 11.67 },
            { skill_name: 'Kafka', skill_type: 'libraries', demand_count: 25100, pct_of_total_postings: 11.09 },
            { skill_name: 'Docker', skill_type: 'other', demand_count: 23400, pct_of_total_postings: 10.34 }
        ],
        'Data Analyst': [
            { skill_name: 'SQL', skill_type: 'programming', demand_count: 168400, pct_of_total_postings: 74.59 },
            { skill_name: 'Excel', skill_type: 'analyst_tools', demand_count: 98500, pct_of_total_postings: 43.63 },
            { skill_name: 'Python', skill_type: 'programming', demand_count: 82100, pct_of_total_postings: 36.36 },
            { skill_name: 'Tableau', skill_type: 'analyst_tools', demand_count: 74200, pct_of_total_postings: 32.87 },
            { skill_name: 'Power BI', skill_type: 'analyst_tools', demand_count: 69800, pct_of_total_postings: 30.92 },
            { skill_name: 'R', skill_type: 'programming', demand_count: 38500, pct_of_total_postings: 17.05 },
            { skill_name: 'Snowflake', skill_type: 'databases', demand_count: 18200, pct_of_total_postings: 8.06 }
        ],
        'Data Scientist': [
            { skill_name: 'Python', skill_type: 'programming', demand_count: 148200, pct_of_total_postings: 74.29 },
            { skill_name: 'SQL', skill_type: 'programming', demand_count: 112400, pct_of_total_postings: 56.35 },
            { skill_name: 'R', skill_type: 'programming', demand_count: 76500, pct_of_total_postings: 38.35 },
            { skill_name: 'Pandas', skill_type: 'libraries', demand_count: 42100, pct_of_total_postings: 21.10 },
            { skill_name: 'PyTorch', skill_type: 'libraries', demand_count: 28400, pct_of_total_postings: 14.24 },
            { skill_name: 'Scikit-Learn', skill_type: 'libraries', demand_count: 24500, pct_of_total_postings: 12.28 }
        ],
        'Machine Learning Engineer': [
            { skill_name: 'Python', skill_type: 'programming', demand_count: 12400, pct_of_total_postings: 88.57 },
            { skill_name: 'PyTorch', skill_type: 'libraries', demand_count: 8600, pct_of_total_postings: 61.43 },
            { skill_name: 'TensorFlow', skill_type: 'libraries', demand_count: 7500, pct_of_total_postings: 53.57 },
            { skill_name: 'SQL', skill_type: 'programming', demand_count: 6800, pct_of_total_postings: 48.57 },
            { skill_name: 'Docker', skill_type: 'other', demand_count: 5900, pct_of_total_postings: 42.14 },
            { skill_name: 'AWS', skill_type: 'cloud', demand_count: 5500, pct_of_total_postings: 39.29 }
        ],
        'Ethical Hacker': [
            { skill_name: 'Vulnerability Assessment', skill_type: 'security', demand_count: 18, pct_of_total_postings: 85.71 },
            { skill_name: 'Penetration Testing', skill_type: 'security', demand_count: 17, pct_of_total_postings: 80.95 },
            { skill_name: 'Bash / Linux', skill_type: 'programming', demand_count: 15, pct_of_total_postings: 71.43 },
            { skill_name: 'Python', skill_type: 'programming', demand_count: 14, pct_of_total_postings: 66.67 },
            { skill_name: 'Cryptography', skill_type: 'security', demand_count: 12, pct_of_total_postings: 57.14 }
        ],
        'AI Prompt Engineer': [
            { skill_name: 'Prompt Engineering', skill_type: 'libraries', demand_count: 25, pct_of_total_postings: 89.29 },
            { skill_name: 'Python', skill_type: 'programming', demand_count: 22, pct_of_total_postings: 78.57 },
            { skill_name: 'LangChain', skill_type: 'libraries', demand_count: 21, pct_of_total_postings: 75.00 },
            { skill_name: 'NLP / LLM Tuning', skill_type: 'libraries', demand_count: 19, pct_of_total_postings: 67.86 },
            { skill_name: 'OpenAI API', skill_type: 'cloud', demand_count: 18, pct_of_total_postings: 64.29 }
        ],
        'Blockchain Developer': [
            { skill_name: 'Solidity', skill_type: 'programming', demand_count: 18, pct_of_total_postings: 85.71 },
            { skill_name: 'Smart Contracts', skill_type: 'libraries', demand_count: 17, pct_of_total_postings: 80.95 },
            { skill_name: 'Web3.js', skill_type: 'libraries', demand_count: 15, pct_of_total_postings: 71.43 },
            { skill_name: 'Rust / Go', skill_type: 'programming', demand_count: 12, pct_of_total_postings: 57.14 }
        ],
        'Big Data Specialist': [
            { skill_name: 'Spark', skill_type: 'libraries', demand_count: 48, pct_of_total_postings: 82.76 },
            { skill_name: 'Python', skill_type: 'programming', demand_count: 42, pct_of_total_postings: 72.41 },
            { skill_name: 'Kafka', skill_type: 'libraries', demand_count: 39, pct_of_total_postings: 67.24 },
            { skill_name: 'Hadoop', skill_type: 'libraries', demand_count: 35, pct_of_total_postings: 60.34 },
            { skill_name: 'Snowflake', skill_type: 'databases', demand_count: 32, pct_of_total_postings: 55.17 }
        ],
        'Game Developer': [
            { skill_name: 'Unity', skill_type: 'libraries', demand_count: 17, pct_of_total_postings: 85.00 },
            { skill_name: 'C++ / C#', skill_type: 'programming', demand_count: 16, pct_of_total_postings: 80.00 },
            { skill_name: 'Unreal Engine', skill_type: 'libraries', demand_count: 14, pct_of_total_postings: 70.00 },
            { skill_name: '3D Graphics', skill_type: 'other', demand_count: 12, pct_of_total_postings: 60.00 }
        ]
    };
    return catalog[role] || [
        { skill_name: 'Python', skill_type: 'programming', demand_count: 238420, pct_of_total_postings: 31.12 },
        { skill_name: 'SQL', skill_type: 'programming', demand_count: 214580, pct_of_total_postings: 28.01 },
        { skill_name: 'R', skill_type: 'programming', demand_count: 95340, pct_of_total_postings: 12.44 },
        { skill_name: 'AWS', skill_type: 'cloud', demand_count: 83920, pct_of_total_postings: 10.95 },
        { skill_name: 'Tableau', skill_type: 'analyst_tools', demand_count: 80150, pct_of_total_postings: 10.46 },
        { skill_name: 'Power BI', skill_type: 'analyst_tools', demand_count: 77240, pct_of_total_postings: 10.08 },
        { skill_name: 'Excel', skill_type: 'analyst_tools', demand_count: 74890, pct_of_total_postings: 9.77 },
        { skill_name: 'Spark', skill_type: 'libraries', demand_count: 52910, pct_of_total_postings: 6.91 },
        { skill_name: 'Azure', skill_type: 'cloud', demand_count: 49840, pct_of_total_postings: 6.50 },
        { skill_name: 'Snowflake', skill_type: 'databases', demand_count: 45210, pct_of_total_postings: 5.90 }
    ];
}

// Dashboard Refresh
async function refreshDashboard() {
    const query = `role=${encodeURIComponent(state.role)}&seniority=${encodeURIComponent(state.seniority)}&country=${encodeURIComponent(state.country)}&remote=${state.remote}&salary_min=${state.salaryMin}`;

    const kpis = await fetchAPI(`/api/kpis?${query}`);
    if (kpis) {
        state.rawKpis = kpis;
        renderKPIs(kpis);
    }

    let skills = await fetchAPI(`/api/skills/matrix?${query}&limit=15`);
    if (!skills || !Array.isArray(skills) || skills.length === 0) {
        skills = getClientFallbackSkills(state.role);
    }

    renderDemandChart(skills);
    renderCategoryChart(skills);
    renderSkillsTable(skills);

    if (state.activeTab === 'roi') loadRoiMatrix();
    if (state.activeTab === 'jobs') loadJobsFeed();
    if (state.activeTab === 'career') runGapAnalysis();
    if (state.activeTab === 'employers') loadEmployers();
}

function setChartMetric(m) {
    state.chartMetric = m;
    document.getElementById('togglePctBtn').className = m === '%' ? 'px-3 py-1 rounded-lg bg-blue-600 text-white' : 'px-3 py-1 rounded-lg text-slate-400 hover:text-white';
    document.getElementById('toggleCountBtn').className = m === 'count' ? 'px-3 py-1 rounded-lg bg-blue-600 text-white' : 'px-3 py-1 rounded-lg text-slate-400 hover:text-white';
    refreshDashboard();
}

// Demand Chart
function renderDemandChart(skills) {
    const canvas = document.getElementById('demandChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (demandChartInstance) demandChartInstance.destroy();

    const safeSkills = (skills && Array.isArray(skills) && skills.length > 0) ? skills : getClientFallbackSkills(state.role);
    const labels = safeSkills.map(s => s.skill_name || 'Tech Skill');
    const dataVals = safeSkills.map(s => state.chartMetric === '%' ? parseFloat(s.pct_of_total_postings || 0) : parseInt(s.demand_count || 0));

    demandChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: state.chartMetric === '%' ? 'Percentage of Postings (%)' : 'Job Count',
                data: dataVals,
                backgroundColor: '#1F77B4',
                borderColor: '#4A9EE0',
                borderWidth: 1,
                borderRadius: 4,
                hoverBackgroundColor: '#4A9EE0'
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${ctx.raw}${state.chartMetric === '%' ? '%' : ' postings'}`
                    }
                }
            },
            scales: {
                x: { grid: { color: '#334155' }, ticks: { color: '#94A3B8', font: { family: 'JetBrains Mono' } } },
                y: { grid: { display: false }, ticks: { color: '#F8FAFC', font: { weight: 'bold' } } }
            }
        }
    });
}

// Category Chart
function renderCategoryChart(skills) {
    const canvas = document.getElementById('categoryChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (categoryChartInstance) categoryChartInstance.destroy();

    const safeSkills = (skills && Array.isArray(skills) && skills.length > 0) ? skills : getClientFallbackSkills(state.role);
    const categories = {};
    safeSkills.forEach(s => {
        const cat = s.skill_type || 'other';
        categories[cat] = (categories[cat] || 0) + (parseInt(s.demand_count) || 100);
    });

    const labels = Object.keys(categories);
    const dataVals = Object.values(categories);
    const colors = ['#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#17BECF', '#E377C2', '#BCBD22'];

    categoryChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataVals,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 2,
                borderColor: '#1E293B'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            cutout: '70%'
        }
    });

    const legendContainer = document.getElementById('categoryLegendContainer');
    if (legendContainer) {
        const totalSum = dataVals.reduce((a, b) => a + b, 0);
        legendContainer.innerHTML = labels.map((cat, i) => {
            const pct = totalSum > 0 ? ((dataVals[i] / totalSum) * 100).toFixed(1) : 0;
            return `
            <div class="flex justify-between items-center">
                <span class="flex items-center gap-1.5 text-slate-300">
                    <span class="w-2.5 h-2.5 rounded-full" style="background-color: ${colors[i % colors.length]}"></span>
                    <span class="capitalize">${cat.replace('_', ' ')}</span>
                </span>
                <span class="font-mono font-bold text-slate-400">${pct}%</span>
            </div>
            `;
        }).join('');
    }
}

function renderSkillsTable(skills) {
    const tbody = document.getElementById('skillsTableBody');
    if (!tbody) return;
    const safeSkills = (skills && Array.isArray(skills) && skills.length > 0) ? skills : getClientFallbackSkills(state.role);
    tbody.innerHTML = safeSkills.map(s => {
        let badgeClass = 'badge-prog';
        if (s.skill_type === 'cloud') badgeClass = 'badge-cloud';
        if (s.skill_type === 'analyst_tools') badgeClass = 'badge-tools';
        if (s.skill_type === 'databases') badgeClass = 'badge-db';
        if (s.skill_type === 'libraries') badgeClass = 'badge-lib';
        if (s.skill_type === 'security') badgeClass = 'badge-sec';

        const pct = s.pct_of_total_postings ? `${parseFloat(s.pct_of_total_postings).toFixed(1)}%` : '—';

        return `
        <tr class="hover:bg-slate-800/40">
            <td class="py-3 px-3 font-bold text-white">${s.skill_name}</td>
            <td class="py-3 px-3"><span class="${badgeClass} text-[10px] px-2 py-0.5 rounded-full uppercase font-bold">${s.skill_type || 'technology'}</span></td>
            <td class="py-3 px-3 text-right font-mono text-slate-300">${(s.demand_count || 0).toLocaleString()}</td>
            <td class="py-3 px-3 text-right font-mono font-bold text-blue-400">${pct}</td>
            <td class="py-3 px-3 text-right">
                <button onclick="filterBySkill('${s.skill_name}')" class="bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white px-2.5 py-1 rounded-lg text-[11px] font-bold">Filter Jobs</button>
            </td>
        </tr>
        `;
    }).join('');
}

function filterBySkill(skillName) {
    state.jobSearch = skillName;
    switchTab('jobs');
    document.getElementById('jobSearchInput').value = skillName;
    loadJobsFeed();
    showToast(`Filtering jobs by skill: ${skillName}`, 'info');
}

// Tech Stack Calculator
function renderCustomStackPills() {
    const container = document.getElementById('customStackPillContainer');
    if (!container) return;

    container.innerHTML = AVAILABLE_STACK_SKILLS.map(s => {
        const isSelected = state.customStack.includes(s.name);
        return `
        <button onclick="toggleCustomStackSkill('${s.name}')" class="px-3 py-1.5 rounded-xl border text-xs font-semibold transition-all flex items-center space-x-1.5 ${isSelected ? 'bg-purple-600 border-purple-400 text-white shadow-lg shadow-purple-500/25' : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-purple-500/50'}">
            <i class="fa-solid ${isSelected ? 'fa-check-square' : 'fa-square'} text-[10px]"></i>
            <span>${s.name}</span>
            <span class="text-[10px] opacity-75 font-mono">(+${(s.uplift / 1000).toFixed(0)}k)</span>
        </button>
        `;
    }).join('');
}

function toggleCustomStackSkill(skillName) {
    if (state.customStack.includes(skillName)) {
        if (state.customStack.length <= 1) {
            showToast('Keep at least 1 skill selected in stack', 'info');
            return;
        }
        state.customStack = state.customStack.filter(s => s !== skillName);
    } else {
        if (state.customStack.length >= 5) {
            showToast('Maximum 5 skills allowed in custom stack calculation', 'info');
            return;
        }
        state.customStack.push(skillName);
    }
    renderCustomStackPills();
    renderCustomStackCalculator();
}

function renderCustomStackCalculator() {
    const baseSalary = (state.rawKpis && state.rawKpis.median_salary) ? state.rawKpis.median_salary : 115000;

    let totalUplift = 0;
    state.customStack.forEach(sName => {
        const item = AVAILABLE_STACK_SKILLS.find(x => x.name === sName);
        if (item) totalUplift += item.uplift;
    });

    // Diminishing returns scaling factor
    totalUplift = Math.round(totalUplift * Math.pow(0.88, state.customStack.length - 1));
    const calculatedSalary = baseSalary + totalUplift;

    document.getElementById('customStackSalaryText').innerText = formatSalary(calculatedSalary, '', '/yr');
    document.getElementById('customStackUpliftText').innerText = `${formatSalary(totalUplift, '+')}/yr Uplift`;
}

// ROI Matrix
async function loadRoiMatrix() {
    const data = await fetchAPI('/api/skills/roi-combo');
    if (!data) return;
    state.rawRoiData = data;
    renderRoiMatrixData(data);
}

function renderRoiMatrixData(data) {
    if (!data) return;
    const cardsContainer = document.getElementById('roiCardsContainer');
    cardsContainer.innerHTML = data.map(c => `
        <div class="glass-card p-4">
            <div class="flex justify-between items-start">
                <span class="text-[11px] font-bold text-purple-400 bg-purple-950/60 px-2 py-0.5 rounded border border-purple-800/40">${c.market_demand_rating}</span>
                <span class="text-emerald-400 font-mono font-black text-xs">+${c.pct_uplift}% Uplift</span>
            </div>
            <h4 class="text-base font-black text-white mt-2">${c.combo_name}</h4>
            <div class="mt-3 space-y-1 text-xs">
                <div class="flex justify-between text-slate-400"><span>Median Salary:</span> <b class="text-white font-mono">${formatSalary(c.median_salary)}</b></div>
                <div class="flex justify-between text-slate-400"><span>Salary Uplift:</span> <b class="text-emerald-400 font-mono">${formatSalary(c.salary_uplift_usd, '+')}</b></div>
                <div class="flex justify-between text-slate-400"><span>Job Volume:</span> <b class="text-slate-300 font-mono">${c.job_count.toLocaleString()} (${c.pct_of_market}%)</b></div>
            </div>
        </div>
    `).join('');

    const tbody = document.getElementById('roiTableBody');
    tbody.innerHTML = data.map(c => `
        <tr class="hover:bg-slate-800/40">
            <td class="py-3 px-3 font-bold text-white">${c.combo_name}</td>
            <td class="py-3 px-3"><div class="flex flex-wrap gap-1">${c.skills.map(s => `<span class="bg-slate-800 text-slate-300 text-[10px] px-2 py-0.5 rounded-full font-mono">${s}</span>`).join('')}</div></td>
            <td class="py-3 px-3 font-bold text-emerald-400">${formatSalary(c.median_salary)}</td>
            <td class="py-3 px-3 text-emerald-400">${formatSalary(c.salary_uplift_usd, '+')}</td>
            <td class="py-3 px-3 font-bold text-emerald-400">+${c.pct_uplift}%</td>
            <td class="py-3 px-3 text-slate-300">${c.job_count.toLocaleString()}</td>
            <td class="py-3 px-3"><span class="bg-purple-950 text-purple-300 text-[10px] font-bold px-2 py-0.5 rounded-full">${c.market_demand_rating}</span></td>
        </tr>
    `).join('');
}

// Jobs Explorer
async function loadJobsFeed() {
    state.jobSort = document.getElementById('jobSortSelect').value;
    const query = `role=${encodeURIComponent(state.role)}&seniority=${encodeURIComponent(state.seniority)}&country=${encodeURIComponent(state.country)}&remote=${state.remote}&salary_min=${state.salaryMin}&search=${encodeURIComponent(state.jobSearch)}&page=${state.jobsPage}&limit=10&sort_by=${state.jobSort}`;
    const res = await fetchAPI(`/api/jobs?${query}`);
    if (!res || !res.jobs) return;
    state.rawJobsRes = res;
    renderJobsFeedData(res);
}

function renderJobsFeedData(res) {
    if (!res || !res.jobs) return;
    document.getElementById('jobsPageSummary').innerText = `Page ${res.page} of ${res.total_pages || 1} (${(res.total_count || 0).toLocaleString()} postings matched)`;
    document.getElementById('prevPageBtn').disabled = res.page <= 1;
    document.getElementById('nextPageBtn').disabled = res.page >= res.total_pages;

    const tbody = document.getElementById('jobsTableBody');
    if (res.jobs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="py-6 text-center text-slate-400 font-semibold">No job postings match your criteria</td></tr>`;
        return;
    }
    tbody.innerHTML = res.jobs.map(j => `
        <tr class="hover:bg-slate-800/40 cursor-pointer transition-all" onclick='openJobDrawer(${JSON.stringify(j).replace(/'/g, "&apos;")})'>
            <td class="py-3 px-4 font-bold text-white">${j.title || 'Data Professional'}</td>
            <td class="py-3 px-4 text-slate-300 font-semibold">${j.company || 'Tech Employer'}</td>
            <td class="py-3 px-4 text-slate-400">${j.location || 'Remote / Global'}</td>
            <td class="py-3 px-4"><span class="bg-purple-950 text-purple-300 text-[10px] font-bold px-2 py-0.5 rounded-full">${j.seniority || 'Mid-Entry'}</span></td>
            <td class="py-3 px-4 font-mono font-bold text-emerald-400">${formatSalary(j.salary_raw, '', '/yr')}</td>
            <td class="py-3 px-4"><div class="flex flex-wrap gap-1">${(j.skills || []).map(s => `<span class="bg-slate-800 text-slate-300 text-[10px] px-1.5 py-0.5 rounded">${s}</span>`).join('')}</div></td>
            <td class="py-3 px-4 text-right">
                <button class="bg-blue-600/20 hover:bg-blue-600 text-blue-400 hover:text-white px-2.5 py-1 rounded-lg text-[11px] font-bold">Quick View</button>
            </td>
        </tr>
    `).join('');
}

function handleJobSearch() {
    state.jobSearch = document.getElementById('jobSearchInput').value;
    state.jobsPage = 1;
    loadJobsFeed();
}

function changeJobPage(delta) {
    state.jobsPage += delta;
    loadJobsFeed();
}

// Job Details Drawer
function openJobDrawer(j) {
    document.getElementById('drawerTitle').innerText = j.title;
    document.getElementById('drawerCompany').innerText = j.company;
    document.getElementById('drawerLocation').innerText = j.location;
    document.getElementById('drawerSalary').innerText = formatSalary(j.salary_raw, '', '/yr');
    document.getElementById('drawerSeniority').innerText = j.seniority;
    document.getElementById('drawerRemote').innerText = j.is_remote ? 'Yes (Work From Home)' : 'On-site / Hybrid';
    document.getElementById('drawerDegree').innerText = j.no_degree ? 'No Degree Required' : 'Degree Preferred';
    document.getElementById('drawerInsurance').innerText = j.health_insurance ? 'Offered' : 'Standard Package';
    document.getElementById('drawerPosted').innerText = j.posted_date;
    document.getElementById('drawerApplyBtn').href = j.apply_link;

    document.getElementById('drawerSkills').innerHTML = j.skills.map(s => `<span class="bg-blue-950 text-blue-300 border border-blue-800/40 text-xs px-2.5 py-1 rounded-lg font-bold">${s}</span>`).join('');

    document.getElementById('jobDrawerOverlay').classList.remove('hidden');
    const drawer = document.getElementById('jobDrawer');
    drawer.classList.remove('drawer-closed');
    drawer.classList.add('drawer-open');
}

function closeJobDrawer() {
    document.getElementById('jobDrawerOverlay').classList.add('hidden');
    const drawer = document.getElementById('jobDrawer');
    drawer.classList.remove('drawer-open');
    drawer.classList.add('drawer-closed');
}

// Career Skill Gap Analyzer
async function runGapAnalysis() {
    const role = document.getElementById('analyzerRoleSelect').value;
    const checkedSkills = Array.from(document.querySelectorAll('#analyzerSkillCheckboxes input:checked')).map(i => i.value);

    const res = await fetchAPI(`/api/career/gap-analysis?target_role=${encodeURIComponent(role)}&current_skills=${encodeURIComponent(checkedSkills.join(','))}`);
    if (!res) return;
    state.rawGapData = res;
    renderGapAnalysisData(res);
    renderCompetencyRadarChart(role, checkedSkills);
}

function renderGapAnalysisData(res) {
    if (!res) return;
    document.getElementById('gapScoreText').innerText = `${res.readiness_score}%`;
    document.getElementById('gapTargetRoleTitle').innerText = res.target_role;

    const rawBoost = (res.potential_salary_boost_raw || 40400);
    document.getElementById('gapSalaryBoostText').innerText = formatSalary(rawBoost, '+', '/yr');

    document.getElementById('gapAcquiredContainer').innerHTML = res.acquired_skills.map(s => `
        <span class="bg-emerald-950 text-emerald-300 border border-emerald-500/30 text-xs px-2.5 py-1 rounded-xl font-bold flex items-center gap-1">
            <i class="fa-solid fa-check text-[10px]"></i> ${s.name}
        </span>
    `).join('') || '<span class="text-xs text-slate-500">None selected</span>';

    document.getElementById('gapMissingContainer').innerHTML = res.missing_skills.map(s => `
        <div class="bg-slate-950 p-3 rounded-xl border border-slate-800 flex justify-between items-center text-xs">
            <div>
                <b class="text-white text-sm block">${s.name}</b>
                <span class="text-slate-400">${s.demand_pct}% Market Demand • ${s.priority}</span>
            </div>
            <span class="text-emerald-400 font-mono font-extrabold bg-emerald-950/60 px-2.5 py-1 rounded-lg border border-emerald-500/30">${formatSalary(s.salary_impact_raw || 12000, '+')}</span>
        </div>
    `).join('') || '<div class="text-xs text-emerald-400 font-bold p-3">🎉 All core skills acquired for this role!</div>';
}

function renderCompetencyRadarChart(targetRole, checkedSkills) {
    const ctx = document.getElementById('radarChart').getContext('2d');
    if (radarChartInstance) radarChartInstance.destroy();

    const allSkills = ['SQL', 'Python', 'AWS', 'Spark', 'PyTorch', 'Snowflake', 'Airflow', 'Tableau'];
    const targetBenchmark = {
        'Data Engineer': [90, 85, 80, 75, 40, 70, 85, 40],
        'Machine Learning Engineer': [70, 95, 85, 60, 90, 40, 50, 30],
        'Data Scientist': [80, 95, 60, 50, 80, 50, 40, 60],
        'Data Analyst': [85, 75, 40, 30, 20, 60, 30, 90]
    }[targetRole] || [80, 80, 60, 60, 60, 60, 60, 60];

    const userScores = allSkills.map(s => checkedSkills.includes(s) ? 90 : 20);

    radarChartInstance = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: allSkills,
            datasets: [
                {
                    label: `${targetRole} Benchmark`,
                    data: targetBenchmark,
                    backgroundColor: 'rgba(31, 119, 180, 0.25)',
                    borderColor: '#1F77B4',
                    borderWidth: 2
                },
                {
                    label: 'Your Current Stack',
                    data: userScores,
                    backgroundColor: 'rgba(44, 160, 44, 0.25)',
                    borderColor: '#2CA02C',
                    borderWidth: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: { color: '#334155' },
                    grid: { color: '#334155' },
                    pointLabels: { color: '#F8FAFC', font: { size: 11, weight: 'bold' } },
                    ticks: { display: false, max: 100 }
                }
            },
            plugins: {
                legend: { labels: { color: '#F3F4F6', font: { family: 'Plus Jakarta Sans' } } }
            }
        }
    });
}

// Top Employers Leaderboard
async function loadEmployers() {
    const query = `role=${encodeURIComponent(state.role)}&seniority=${encodeURIComponent(state.seniority)}&country=${encodeURIComponent(state.country)}&remote=${state.remote}`;
    const data = await fetchAPI(`/api/employers/top?${query}`);
    if (!data) return;
    state.rawEmployersData = data;
    renderEmployersData(data);
    renderEmployersChart(data);
}

function renderEmployersData(data) {
    if (!data) return;
    const tbody = document.getElementById('employersTableBody');
    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" class="py-6 text-center text-slate-400 font-semibold">No employer data found for current filters</td></tr>`;
        return;
    }
    tbody.innerHTML = data.map(e => `
        <tr class="hover:bg-slate-800/40">
            <td class="py-3 px-3 font-bold text-white">${e.company_name || 'Unknown Company'}</td>
            <td class="py-3 px-3 text-right text-slate-300">${(e.total_postings || 0).toLocaleString()}</td>
            <td class="py-3 px-3 text-right text-amber-400">${(e.salaried_postings_count || 0).toLocaleString()}</td>
            <td class="py-3 px-3 text-right font-bold text-emerald-400">${formatSalary(e.avg_salary_usd)}</td>
        </tr>
    `).join('');
}

function renderEmployersChart(data) {
    const ctx = document.getElementById('employersChart').getContext('2d');
    if (employersChartInstance) employersChartInstance.destroy();

    const topData = data.slice(0, 10);
    const labels = topData.map(e => e.company_name);
    const salaries = topData.map(e => {
        const curr = CURRENCIES[state.currency] || CURRENCIES.USD;
        return Math.round((e.avg_salary_usd || 120000) * curr.rate);
    });

    employersChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: `Average Salary (${state.currency})`,
                data: salaries,
                backgroundColor: '#17BECF',
                borderColor: '#4ED2DF',
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: (ctx) => `${CURRENCIES[state.currency].symbol}${ctx.raw.toLocaleString()}`
                    }
                }
            },
            scales: {
                x: { grid: { display: false }, ticks: { color: '#F3F4F6', font: { weight: 'bold' } } },
                y: { grid: { color: '#1E294B' }, ticks: { color: '#94A3B8', font: { family: 'JetBrains Mono' } } }
            }
        }
    });
}

// Currency Converter Modal
function openCurrencyConverterModal() {
    const initialVal = (state.rawKpis && state.rawKpis.median_salary) ? state.rawKpis.median_salary : 115000;
    document.getElementById('converterAmountInput').value = initialVal;
    updateCurrencyConverterModal();
    document.getElementById('currencyModalOverlay').classList.remove('hidden');
    document.getElementById('currencyModal').classList.remove('hidden');
}

function closeCurrencyConverterModal() {
    document.getElementById('currencyModalOverlay').classList.add('hidden');
    document.getElementById('currencyModal').classList.add('hidden');
}

function updateCurrencyConverterModal() {
    let usdAmount = parseFloat(document.getElementById('converterAmountInput').value) || 0;
    const period = document.getElementById('converterPeriodSelect').value;

    let multiplier = 1;
    let periodSuffix = '/yr';
    if (period === 'month') {
        multiplier = 1 / 12;
        periodSuffix = '/mo';
    } else if (period === 'hour') {
        multiplier = 1 / 2080;
        periodSuffix = '/hr';
    }

    const grid = document.getElementById('currencyCardsGrid');
    if (!grid) return;

    grid.innerHTML = Object.values(CURRENCIES).map(c => {
        const val = usdAmount * c.rate * multiplier;
        const formatted = Math.round(val).toLocaleString();
        const isActive = c.code === state.currency;
        return `
            <div onclick="setCurrency('${c.code}')" class="cursor-pointer p-3 rounded-xl border transition-all ${isActive ? 'bg-emerald-950/80 border-emerald-500 shadow-lg shadow-emerald-500/20' : 'bg-slate-950 border-slate-800 hover:border-emerald-500/50'}">
                <div class="flex justify-between items-center text-xs mb-1">
                    <span class="font-bold text-slate-300 flex items-center gap-1.5"><span class="text-base">${c.flag}</span> ${c.code}</span>
                    <span class="text-[10px] text-slate-500 font-mono">1 USD = ${c.rate}</span>
                </div>
                <div class="text-sm font-black font-mono text-white mt-1">${c.symbol}${formatted} <span class="text-[10px] text-emerald-400 font-bold font-sans">${periodSuffix}</span></div>
            </div>
        `;
    }).join('');
}

// Command Palette (Ctrl+K)
function openCommandPalette() {
    document.getElementById('commandPaletteOverlay').classList.remove('hidden');
    document.getElementById('commandPaletteModal').classList.remove('hidden');
    document.getElementById('commandInput').focus();
}

function closeCommandPalette() {
    document.getElementById('commandPaletteOverlay').classList.add('hidden');
    document.getElementById('commandPaletteModal').classList.add('hidden');
}

function filterCommandPalette() {
    const query = document.getElementById('commandInput').value.toLowerCase();
    const items = document.querySelectorAll('#commandList > div');
    items.forEach(item => {
        const text = item.innerText.toLowerCase();
        item.style.display = text.includes(query) ? 'flex' : 'none';
    });
}

function executeCommand(cmd) {
    closeCommandPalette();
    if (['demand', 'roi', 'jobs', 'career', 'employers'].includes(cmd)) {
        switchTab(cmd);
    } else if (cmd === 'converter') {
        openCurrencyConverterModal();
    } else if (cmd === 'export-pdf') {
        printExecutiveReport();
    } else if (cmd === 'share') {
        copyShareableLink();
    } else if (cmd === 'diagnostics') {
        openDiagnosticsModal();
    }
}

// Data Export Handlers
function exportCurrentViewCSV() {
    if (state.activeTab === 'jobs') exportJobsCSV();
    else if (state.activeTab === 'employers') exportEmployersCSV();
    else if (state.activeTab === 'roi') exportRoiCSV();
    else exportSkillDemandCSV();
}

function exportSkillDemandCSV() {
    if (!state.rawKpis) return;
    const rows = [
        ['Metric', 'Value'],
        ['Filtered Job Volume', state.rawKpis.total_postings],
        ['Median Annual Salary (USD)', state.rawKpis.median_salary],
        ['Top Skill', state.rawKpis.top_skill],
        ['Top Combo', state.rawKpis.top_combo]
    ];
    downloadCSV(rows, 'skill_demand_analytics.csv');
}

function exportJobsCSV() {
    if (!state.rawJobsRes || !state.rawJobsRes.jobs) return;
    const headers = ['Title', 'Company', 'Location', 'Seniority', 'Salary (USD)', 'Skills'];
    const data = state.rawJobsRes.jobs.map(j => [
        j.title, j.company, j.location, j.seniority, j.salary_raw || 'Undisclosed', (j.skills || []).join(';')
    ]);
    downloadCSV([headers, ...data], 'filtered_jobs_export.csv');
}

function exportEmployersCSV() {
    if (!state.rawEmployersData) return;
    const headers = ['Company Name', 'Total Job Postings', 'Salaried Postings', 'Average Salary (USD)'];
    const data = state.rawEmployersData.map(e => [
        e.company_name, e.total_postings, e.salaried_postings_count, e.avg_salary_usd
    ]);
    downloadCSV([headers, ...data], 'top_employers_export.csv');
}

function exportRoiCSV() {
    if (!state.rawRoiData) return;
    const headers = ['Tech Combination', 'Skills', 'Median Salary (USD)', 'Salary Uplift (USD)', 'Uplift %', 'Job Count', 'Demand Rating'];
    const data = state.rawRoiData.map(c => [
        c.combo_name, c.skills.join(';'), c.median_salary, c.salary_uplift_usd, c.pct_uplift, c.job_count, c.market_demand_rating
    ]);
    downloadCSV([headers, ...data], 'skill_combo_roi_export.csv');
}

function downloadCSV(rows, filename) {
    const csvContent = "data:text/csv;charset=utf-8," + rows.map(e => e.map(x => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast(`Exported ${filename} successfully`, 'success');
}

function printExecutiveReport() {
    showToast('Preparing executive print report...', 'info');
    setTimeout(() => window.print(), 500);
}

function copyShareableLink() {
    updateURL();
    navigator.clipboard.writeText(window.location.href).then(() => {
        showToast('Shareable workspace URL copied to clipboard!', 'success');
    }).catch(() => {
        showToast('URL updated in browser bar', 'info');
    });
}

// Onboarding Tour
const onboardingSteps = [
    {
        title: "Welcome to Tech Job Market Analytics",
        subtitle: "Step 1 of 4 • Platform Overview",
        content: `
            <div class="space-y-3">
                <div class="p-3.5 bg-blue-950/40 border border-blue-500/30 rounded-xl flex items-center gap-3">
                    <i class="fa-solid fa-database text-blue-400 text-2xl"></i>
                    <div>
                        <div class="font-bold text-white text-sm">767,000+ Job Postings Analyzed</div>
                        <div class="text-xs text-slate-400">Powered by PostgreSQL Materialized Views & sub-millisecond query engine.</div>
                    </div>
                </div>
                <p class="text-slate-300 text-xs leading-relaxed">This analytics platform provides quantitative insights into technical skill demand, compensation benchmarks, employer hiring patterns, and remote work conditions for tech professionals.</p>
            </div>
        `
    },
    {
        title: "Interactive Filters & Role Slicers",
        subtitle: "Step 2 of 4 • Dynamic Workspace Filtering",
        content: `
            <div class="space-y-3">
                <p class="text-xs text-slate-300">Customise your view using the sticky top filter bar:</p>
                <div class="space-y-2 text-xs">
                    <div class="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800 flex items-start gap-2.5">
                        <i class="fa-solid fa-filter text-blue-400 mt-0.5"></i>
                        <div><b class="text-white">Role Slicers:</b> Instantly filter by Data Engineer, Data Scientist, ML Engineer, Data Analyst, Software Engineer, Cloud Engineer, etc.</div>
                    </div>
                    <div class="p-2.5 bg-slate-950/80 rounded-xl border border-slate-800 flex items-start gap-2.5">
                        <i class="fa-solid fa-layer-group text-indigo-400 mt-0.5"></i>
                        <div><b class="text-white">Seniority & Country:</b> Filter postings by Senior vs Mid-Entry levels and specific geographic markets.</div>
                    </div>
                </div>
            </div>
        `
    },
    {
        title: "5 Core Analytics Modules",
        subtitle: "Step 3 of 4 • Dashboard Navigation",
        content: `
            <div class="space-y-2 text-xs">
                <div class="p-2 bg-slate-950 rounded-xl border border-slate-800"><span class="text-amber-400 font-bold">🔥 Skills Demand:</span> Ranked penetration leaderboard & top tech skills distribution.</div>
                <div class="p-2 bg-slate-950 rounded-xl border border-slate-800"><span class="text-purple-400 font-bold">⚡ Skill Combo ROI:</span> Real-time salary uplift calculator for multi-skill tech stacks.</div>
                <div class="p-2 bg-slate-950 rounded-xl border border-slate-800"><span class="text-cyan-400 font-bold">📋 Job Explorer Grid:</span> Paginated search feed of individual hiring opportunities.</div>
                <div class="p-2 bg-slate-950 rounded-xl border border-slate-800"><span class="text-rose-400 font-bold">🎯 Career Skill Gap Planner:</span> Personalised skill gap analysis & salary growth calculator.</div>
                <div class="p-2 bg-slate-950 rounded-xl border border-slate-800"><span class="text-emerald-400 font-bold">🏢 Top Employers:</span> Leaderboard of top tech hiring companies & average compensation.</div>
            </div>
        `
    },
    {
        title: "Power Tools & Data Export",
        subtitle: "Step 4 of 4 • Advanced Productivity",
        content: `
            <div class="space-y-3 text-xs">
                <div class="grid grid-cols-2 gap-2">
                    <div class="p-2.5 bg-slate-950 rounded-xl border border-slate-800">
                        <div class="font-bold text-white"><i class="fa-solid fa-terminal text-blue-400"></i> Command Palette</div>
                        <div class="text-slate-400 text-[11px] mt-0.5">Press <kbd class="bg-slate-800 text-slate-300 px-1 rounded">Ctrl+K</kbd> to jump anywhere instantly.</div>
                    </div>
                    <div class="p-2.5 bg-slate-950 rounded-xl border border-slate-800">
                        <div class="font-bold text-white"><i class="fa-solid fa-download text-emerald-400"></i> CSV & PDF Export</div>
                        <div class="text-slate-400 text-[11px] mt-0.5">One-click export for datasets or printable executive PDF reports.</div>
                    </div>
                </div>
                <div class="p-3 bg-emerald-950/40 border border-emerald-500/30 rounded-xl text-emerald-300 font-semibold text-center">
                    🚀 You are all set! Click 'Got It!' to start exploring.
                </div>
            </div>
        `
    }
];

let currentOnboardingStep = 0;

function startOnboardingTour() {
    currentOnboardingStep = 0;
    renderOnboardingStep();
    document.getElementById('onboardingOverlay').classList.remove('hidden');
    document.getElementById('onboardingModal').classList.remove('hidden');
}

function closeOnboardingTour() {
    document.getElementById('onboardingOverlay').classList.add('hidden');
    document.getElementById('onboardingModal').classList.add('hidden');
    localStorage.setItem('hasSeenOnboarding', 'true');
}

function renderOnboardingStep() {
    const step = onboardingSteps[currentOnboardingStep];
    document.getElementById('onboardingStepTitle').innerText = step.title;
    document.getElementById('onboardingStepSubtitle').innerText = step.subtitle;
    document.getElementById('onboardingStepContent').innerHTML = step.content;

    const dotsContainer = document.getElementById('onboardingDots');
    dotsContainer.innerHTML = onboardingSteps.map((_, idx) => `
        <span class="h-2 rounded-full transition-all ${idx === currentOnboardingStep ? 'bg-blue-500 w-6' : 'bg-slate-700 w-2'}"></span>
    `).join('');

    const prevBtn = document.getElementById('onboardingPrevBtn');
    const nextBtn = document.getElementById('onboardingNextBtn');

    if (currentOnboardingStep === 0) {
        prevBtn.classList.add('hidden');
    } else {
        prevBtn.classList.remove('hidden');
    }

    if (currentOnboardingStep === onboardingSteps.length - 1) {
        nextBtn.innerHTML = 'Got It! <i class="fa-solid fa-check ml-1"></i>';
    } else {
        nextBtn.innerHTML = 'Next Step <i class="fa-solid fa-arrow-right ml-1"></i>';
    }
}

function nextOnboardingStep() {
    if (currentOnboardingStep < onboardingSteps.length - 1) {
        currentOnboardingStep++;
        renderOnboardingStep();
    } else {
        closeOnboardingTour();
    }
}

function prevOnboardingStep() {
    if (currentOnboardingStep > 0) {
        currentOnboardingStep--;
        renderOnboardingStep();
    }
}

window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const initialTab = urlParams.get('tab');

    if (initialTab && ['demand', 'roi', 'jobs', 'career', 'employers'].includes(initialTab)) {
        switchTab(initialTab);
    }

    // Trigger onboarding tour on page load
    setTimeout(startOnboardingTour, 600);
});

// Global Keyboard Shortcuts
window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        openCommandPalette();
    } else if (e.key === 'Escape') {
        closeCommandPalette();
        closeJobDrawer();
        closeCurrencyConverterModal();
        closeDiagnosticsModal();
        closeOnboardingTour();
    }
});

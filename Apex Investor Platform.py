import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import warnings
import json
import bcrypt
from email_validator import validate_email, EmailNotValidError
import time
import os

warnings.filterwarnings('ignore')

# --- CONFIGURATION & SETUP ---

# Page configuration
st.set_page_config(
    page_title="Apex Investor Platform",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme and professional styling
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
        background-color: #0e1117;
    }
    .investment-card {
        background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
        padding: 2rem;
        border-radius: 1rem;
        color: white;
        margin: 1rem 0;
        border: 2px solid #475569;
    }
    .metric-card {
        background: linear-gradient(135deg, #1f2937 0%, #374151 100%);
        padding: 1.2rem;
        border-radius: 0.8rem;
        border: 2px solid #6b7280;
        margin: 0.3rem 0;
        color: white;
    }
    .metric-title {
        color: #d1d5db;
        font-size: 0.9rem;
        margin: 0 0 0.5rem 0;
        font-weight: 500;
    }
    .metric-value {
        color: #ffffff;
        font-size: 1.3rem;
        margin: 0;
        font-weight: bold;
    }
    .success-message {
        background: linear-gradient(135deg, #064e3b 0%, #047857 100%);
        padding: 1.5rem;
        border-radius: 0.8rem;
        color: white;
        text-align: center;
        font-weight: bold;
        font-size: 1.1rem;
        border: 2px solid #10b981;
        margin: 1rem 0;
    }
    .motivational-message {
        background: linear-gradient(135deg, #92400e 0%, #b45309 100%);
        padding: 1.5rem;
        border-radius: 0.8rem;
        color: white;
        text-align: center;
        font-weight: bold;
        font-size: 1.1rem;
        border: 2px solid #f59e0b;
        margin: 1rem 0;
    }
    .info-box {
        background: linear-gradient(135deg, #1e3a8a 0%, #3730a3 100%);
        padding: 1.2rem;
        border-radius: 0.8rem;
        color: white;
        border: 2px solid #6366f1;
        margin: 0.5rem 0;
    }
    .stSelectbox > div > div { background-color: #374151; color: white; }
    .stNumberInput > div > div > input { background-color: #374151; color: white; }
    .stSlider > div > div > div { background-color: #374151; }
    .scenario-header {
        background: linear-gradient(135deg, #312e81 0%, #1e1b4b 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
        margin: 0.5rem 0;
        border: 2px solid #6366f1;
    }
</style>
""", unsafe_allow_html=True)

# Educational pop-ups data
EDUCATIONAL_CONTENT = {
    "mutual_funds": {"title": "📊 Mutual Funds", "content": """
        **What are Mutual Funds?**
        - Pool of money from many investors
        - Professionally managed by fund managers  
        - Diversified portfolio of stocks, bonds, or other securities
        - Suitable for long-term wealth creation
        """},
    "stocks": {"title": "📈 Stocks", "content": """
        **What are Stocks?**
        - Ownership shares in a company
        - Potential for high returns but volatile
        - Requires research and market knowledge
        - Best for long-term investment
        """},
    "fd": {"title": "🏛️ Fixed Deposits", "content": """
        **What are Fixed Deposits?**
        - Safe investment with guaranteed returns
        - Fixed interest rate for specific tenure
        - No market risk involved
        - Lower returns compared to equity
        """},
    "bonds": {"title": "📜 Bonds", "content": """
        **What are Bonds?**
        - Debt instruments issued by companies/government
        - Regular interest payments (coupon)
        - Lower risk than stocks
        - Good for steady income
        """},
    "aif": {"title": "🎯 Alternative Investment Funds", "content": """
        **What are AIFs?**
        - Privately pooled investment funds
        - Higher minimum investment
        - Less regulated than mutual funds
        - Potential for higher returns
        """}
}

# --- HELPER FUNCTIONS ---

def calculate_returns(amount, years, monthly_investment, allocation, scenario='normal', inflation=0.0):
    """Calculate returns with inflation adjustment"""
    
    asset_returns = {
        'normal': {'mutual_funds': 0.12, 'stocks': 0.15, 'fd': 0.06, 'bonds': 0.07, 'aif': 0.18},
        'bullish': {'mutual_funds': 0.18, 'stocks': 0.25, 'fd': 0.06, 'bonds': 0.07, 'aif': 0.28},
        'bearish': {'mutual_funds': 0.04, 'stocks': 0.02, 'fd': 0.06, 'bonds': 0.07, 'aif': 0.08}
    }
    asset_risks = {
        'mutual_funds': 0.18, 'stocks': 0.25, 'fd': 0.02, 'bonds': 0.05, 'aif': 0.30
    }
    asset_betas = {
        'mutual_funds': 0.85, 'stocks': 1.2, 'fd': 0.0, 'bonds': 0.1, 'aif': 1.5
    }
    
    returns = asset_returns[scenario]
    portfolio_return = sum(allocation.get(asset, 0) * returns.get(asset, 0) for asset in allocation)
    
    months = years * 12
    monthly_return = portfolio_return / 12
    
    fv_lumpsum = amount * (1 + portfolio_return) ** years
    
    if monthly_investment > 0:
        fv_monthly = monthly_investment * (((1 + monthly_return) ** months - 1) / monthly_return)
    else:
        fv_monthly = 0
    
    total_future_value = fv_lumpsum + fv_monthly
    total_investment = amount + (monthly_investment * months)
    
    if inflation > 0:
        real_future_value = total_future_value / ((1 + inflation) ** years)
    else:
        real_future_value = total_future_value
    
    return {
        'total_investment': total_investment,
        'future_value': total_future_value,
        'real_future_value': real_future_value,
        'gains': total_future_value - total_investment,
        'portfolio_return': portfolio_return,
        'portfolio_risk': sum(allocation.get(asset, 0) * asset_risks.get(asset, 0) for asset in allocation),
        'portfolio_beta': sum(allocation.get(asset, 0) * asset_betas.get(asset, 0) for asset in allocation)
    }

def create_metric_card(title, value, color="#ffffff"):
    """Create a dark themed metric card"""
    return f"""
    <div class="metric-card">
        <h4 class="metric-title">{title}</h4>
        <h3 class="metric-value" style="color: {color};">{value}</h3>
    </div>
    """

def show_educational_popup(content_key):
    """Show educational content in an expander"""
    if content_key in EDUCATIONAL_CONTENT:
        content = EDUCATIONAL_CONTENT[content_key]
        with st.expander(f"💡 Learn about {content['title']}", expanded=False):
            st.markdown(content['content'])

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

# --- STATE MANAGEMENT & SESSION ---

if 'phase' not in st.session_state:
    st.session_state.phase = 1
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'subscribed' not in st.session_state:
    st.session_state.subscribed = False
if 'user_data' not in st.session_state:
    if not os.path.exists('users.json'):
        with open('users.json', 'w') as f:
            json.dump({}, f)
    
    try:
        with open('users.json', 'r') as f:
            st.session_state.user_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        st.session_state.user_data = {}

# --- PHASE 1: FREE EDUCATIONAL TOOL ---

def phase_1():
    st.markdown("""
    <div class="investment-card">
        <h1>Apex Investor Platform</h1>
        <p>Unlock your financial potential by visualizing investment outcomes.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.header("📊 Investment Parameters")
    
    investment_type = st.sidebar.radio("Choose your investment approach:", ["Lump Sum", "SIP"], help="Select a one-time or monthly investment")
    
    if investment_type == "Lump Sum":
        initial_amount = st.sidebar.number_input("💰 Lump Sum (₹)", min_value=1000, value=100000, step=5000)
        monthly_investment = 0
    else:
        monthly_investment = st.sidebar.number_input("📅 Monthly SIP (₹)", min_value=500, value=5000, step=500)
        initial_amount = 0
    
    time_horizon = st.sidebar.slider("⏱️ Time Horizon (Years)", min_value=1, max_value=30, value=10)
    
    st.sidebar.subheader("📊 Asset Allocation")
    mf_allocation = st.sidebar.slider("Mutual Funds (%)", 0, 100, 40)
    show_educational_popup("mutual_funds")
    stocks_allocation = st.sidebar.slider("Stocks (%)", 0, 100, 20)
    show_educational_popup("stocks")
    fd_allocation = st.sidebar.slider("Fixed Deposits (%)", 0, 100, 20)
    show_educational_popup("fd")
    bonds_allocation = st.sidebar.slider("Bonds (%)", 0, 100, 15)
    show_educational_popup("bonds")
    aif_allocation = st.sidebar.slider("AIF (%)", 0, 100, 5)
    show_educational_popup("aif")

    total_allocation = mf_allocation + stocks_allocation + fd_allocation + bonds_allocation + aif_allocation
    if total_allocation != 100:
        st.sidebar.error(f"Total allocation should be 100%. Current: {total_allocation}%")
        st.stop()
    
    allocation = {
        'mutual_funds': mf_allocation/100, 'stocks': stocks_allocation/100,
        'fd': fd_allocation/100, 'bonds': bonds_allocation/100,
        'aif': aif_allocation/100
    }
    
    st.header("📊 Investment Projections")
    scenarios = ['normal', 'bullish', 'bearish']
    scenario_names = ['Normal Market', 'Bull Market', 'Bear Market']
    results = {scenario: calculate_returns(initial_amount, time_horizon, monthly_investment, allocation, scenario) for scenario in scenarios}

    cols = st.columns(3)
    for i, scenario in enumerate(scenarios):
        with cols[i]:
            st.markdown(f'<div class="scenario-header"><h3>📈 {scenario_names[i]}</h3></div>', unsafe_allow_html=True)
            st.markdown(create_metric_card("Future Value", f"₹{results[scenario]['future_value']:,.0f}"), unsafe_allow_html=True)
            st.markdown(create_metric_card("Total Gains", f"₹{results[scenario]['gains']:,.0f}"), unsafe_allow_html=True)
    
    if st.button("Unlock Advanced Personalized Features (INR 999 Annually)", type="primary"):
        st.session_state.phase = 2
        st.session_state.authenticated = False
        st.rerun()

# --- PHASE 2: AUTHENTICATION & PERSONA BUILDER ---

def phase_2():
    st.markdown("""
    <div class="investment-card">
        <h1>🔐 Account Creation & Persona Builder (Phase 2)</h1>
        <p>Unlock personalized insights and goal-based planning</p>
    </div>
    """, unsafe_allow_html=True)

    if not st.session_state.authenticated:
        st.subheader("Login or Sign Up")
        
        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            with st.form("login_form"):
                st.write("Login to your account")
                email = st.text_input("Email", key="login_email")
                password = st.text_input("Password", type="password", key="login_password")
                submitted = st.form_submit_button("Login")
                if submitted:
                    user = st.session_state.user_data.get(email)
                    if user and check_password(password, user['password']):
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.success("Logged in successfully!")
                        st.session_state.phase = 3 
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
        
        with tab2:
            with st.form("signup_form"):
                st.write("Create a new account")
                new_email = st.text_input("Email", key="signup_email")
                new_password = st.text_input("Password", type="password", key="signup_password")
                submitted = st.form_submit_button("Sign Up")
                if submitted:
                    if not new_email or not new_password:
                        st.error("Email and Password are required.")
                    elif new_email in st.session_state.user_data:
                        st.error("An account with this email already exists.")
                    else:
                        try:
                            validate_email(new_email, check_deliverability=False)
                            hashed_password = hash_password(new_password)
                            st.session_state.user_data[new_email] = {'password': hashed_password, 'is_subscribed': False, 'persona': {}, 'goals': []}
                            with open('users.json', 'w') as f:
                                json.dump(st.session_state.user_data, f)
                            st.success("Account created successfully! Please log in.")
                        except EmailNotValidError:
                            st.error("Please enter a valid email address.")

# --- PHASE 3: DEEP DIVE SIMULATION ---

def phase_3():
    st.markdown("""
    <div class="investment-card">
        <h1>🎯 Goal-Based Planning & Simulation (Phase 3)</h1>
        <p>Build your personalized portfolio with tailored insights</p>
    </div>
    """, unsafe_allow_html=True)

    user_data = st.session_state.user_data[st.session_state.user_email]

    if not user_data['is_subscribed']:
        st.markdown("""
        <div class="info-box">
            To unlock advanced features like goal-based planning, please subscribe.
        </div>
        """, unsafe_allow_html=True)
        st.subheader("Your Subscription")
        st.markdown("Annual Subscription: **INR 999**")
        if st.button("Simulate Payment & Subscribe", type="primary"):
            st.session_state.user_data[st.session_state.user_email]['is_subscribed'] = True
            with open('users.json', 'w') as f:
                json.dump(st.session_state.user_data, f)
            st.success("Subscription successful! You now have access to premium features.")
            st.rerun()
        st.stop()
        
    with st.expander("📝 Complete Your Investor Persona", expanded=not user_data['persona']):
        st.subheader("Financial Health & Risk Profile")
        with st.form("persona_form"):
            income = st.number_input("Annual Income (INR)", min_value=10000, step=10000)
            assets = st.number_input("Total Assets (excluding this investment)", min_value=0, step=100000)
            emergency_fund = st.radio("Do you have 6 months of salary saved as an emergency fund?", ["Yes", "No"])
            
            st.markdown("---")
            st.subheader("Risk Profile Questionnaire")
            q1 = st.radio("1. What would you do if your portfolio value dropped by 20% in a single month?",
                ["Sell everything to cut my losses", "Sell some to rebalance", "Hold and wait for recovery", "Buy more to average out the cost"])
            q2 = st.radio("2. What is your primary goal for this investment?",
                ["Capital protection", "Steady income", "Balanced growth", "Aggressive growth"])
            q3 = st.radio("3. What is your investment horizon?",
                ["1-3 years", "3-5 years", "5-10 years", "10+ years"])
            
            submitted = st.form_submit_button("Save Persona & Goals")
            
            if submitted:
                risk_score = (
                    (1 if q1 == "Sell everything to cut my losses" else 2 if q1 == "Sell some to rebalance" else 3 if q1 == "Hold and wait for recovery" else 4) +
                    (1 if q2 == "Capital protection" else 2 if q2 == "Steady income" else 3 if q2 == "Balanced growth" else 4) +
                    (1 if q3 == "1-3 years" else 2 if q3 == "3-5 years" else 3 if q3 == "5-10 years" else 4)
                )
                
                risk_profile = "Conservative" if risk_score <= 5 else "Moderately Conservative" if risk_score <= 8 else "Moderate" if risk_score <= 10 else "Moderately Aggressive" if risk_score <= 12 else "Aggressive"
                
                user_data['persona'] = {'income': income, 'assets': assets, 'emergency_fund': emergency_fund, 'risk_profile': risk_profile}
                
                with open('users.json', 'w') as f:
                    json.dump(st.session_state.user_data, f)
                st.success(f"Persona saved. Your risk profile is: **{risk_profile}**")
                st.rerun()

    if user_data['persona']:
        st.subheader("Your Investor Persona")
        st.info(f"Risk Profile: **{user_data['persona']['risk_profile']}**")

        st.subheader("Define Your Financial Goals")
        goal_name = st.text_input("Goal Name (e.g., Retirement)", key='goal_name')
        goal_target = st.number_input("Target Amount (₹)", min_value=10000, step=10000, key='goal_target')
        goal_horizon = st.slider("Time Horizon (Years)", min_value=1, max_value=30, value=10, key='goal_horizon')
        
        if st.button("Add Goal"):
            if goal_name and goal_target > 0:
                user_data['goals'].append({'name': goal_name, 'target': goal_target, 'horizon': goal_horizon})
                with open('users.json', 'w') as f:
                    json.dump(st.session_state.user_data, f)
                st.success(f"Goal '{goal_name}' added.")
            else:
                st.error("Please enter a valid goal name and target amount.")

        if user_data['goals']:
            st.subheader("Refined Portfolio Simulation")
            goal_to_simulate = st.selectbox("Select a goal to simulate:", [goal['name'] for goal in user_data['goals']])
            selected_goal = next(g for g in user_data['goals'] if g['name'] == goal_to_simulate)

            risk_map = {"Conservative": 20, "Moderately Conservative": 35, "Moderate": 50, "Moderately Aggressive": 65, "Aggressive": 80}
            default_equity = risk_map.get(user_data['persona']['risk_profile'], 50)
            
            st.subheader(f"Simulating for Goal: '{selected_goal['name']}'")
            st.info(f"Target: ₹{selected_goal['target']:,} | Horizon: {selected_goal['horizon']} years")
            
            with st.container(border=True):
                st.subheader("Refined Allocation (excluding FD/Bonds)")
                mutual_funds_eq_alloc = st.slider("Equity Mutual Funds (%)", 0, 100, default_equity)
                mutual_funds_debt_alloc = st.slider("Debt Mutual Funds (%)", 0, 100, 100 - default_equity)
                aif_alloc = st.slider("AIF (%)", 0, 100, 0)
                stocks_alloc = st.slider("Direct Stocks (%)", 0, 100, 0)
                
                total_refined = mutual_funds_eq_alloc + mutual_funds_debt_alloc + aif_alloc + stocks_alloc
                if total_refined != 100:
                    st.error(f"Total refined allocation must be 100%. Current: {total_refined}%")
                    st.stop()
                    
                allocation_refined = {
                    'mutual_funds': (mutual_funds_eq_alloc + mutual_funds_debt_alloc) / 100,
                    'stocks': stocks_alloc / 100,
                    'aif': aif_alloc / 100
                }

                initial_investment = st.number_input("Initial Investment (₹)", value=0)
                monthly_sip = st.number_input("Monthly SIP (₹)", value=5000)

                result_normal = calculate_returns(initial_investment, selected_goal['horizon'], monthly_sip, allocation_refined, 'normal', 0.045)
                
                st.subheader("Simulated Outcome (Fixed 4.5% Inflation)")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Projected Future Value", f"₹{result_normal['future_value']:,.0f}")
                with col2:
                    st.metric("Inflation-Adjusted Value", f"₹{result_normal['real_future_value']:,.0f}")

                if st.button("Ready to turn your plan into reality? Continue to invest.", type="primary"):
                    st.session_state.phase = 4
                    st.session_state.final_plan = {
                        'goal': selected_goal,
                        'initial': initial_investment,
                        'sip': monthly_sip,
                        'allocation': allocation_refined,
                        'results': result_normal
                    }
                    st.rerun()

# --- PHASE 4: KYC & EXECUTION GATEWAY ---

def phase_4():
    st.markdown("""
    <div class="investment-card">
        <h1>✅ Real-World Investment Gateway (Phase 4)</h1>
        <p>Complete your regulatory and compliance steps</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="info-box">
        <strong>⚠️ IMPORTANT:</strong> This is a simulated process to demonstrate the steps required for actual investment.
        All data entered here is for educational purposes and will not be submitted to any authority.
    </div>
    """, unsafe_allow_html=True)

    with st.form("kyc_form"):
        st.subheader("1. Full KYC & Statutory Requirements (SEBI-Compliant)")
        st.text_input("Full Name as per PAN")
        st.text_input("PAN Card Number")
        st.file_uploader("Upload PAN Card Photo")
        st.text_input("Aadhaar Card Number")
        st.file_uploader("Upload Aadhaar Card Photo")
        st.text_input("Bank Account Number")
        st.text_input("IFSC Code")
        
        st.subheader("2. Other Statutory Declarations")
        st.checkbox("I declare that I am a tax resident of India and not a tax resident of any other country (FATCA).")
        st.text_input("Nominee Name")
        st.text_input("Nominee Relationship")
        
        submitted = st.form_submit_button("Submit KYC & Statutory Details")

        if submitted:
            st.success("KYC and statutory details submitted successfully! This is a mock submission.")
            st.session_state.phase = 5
            st.rerun()

# --- PHASE 5: RECOMMENDATIONS & REPORTING ---

def phase_5():
    st.markdown("""
    <div class="investment-card">
        <h1>🌟 Intelligent Recommendations & Reporting (Phase 5)</h1>
        <p>Get expert insights and a professional-grade report for your plan</p>
    </div>
    """, unsafe_allow_html=True)
    
    final_plan = st.session_state.final_plan
    user_persona = st.session_state.user_data[st.session_state.user_email]['persona']
    
    st.subheader(f"Final Investment Plan for Goal: {final_plan['goal']['name']}")
    st.markdown(f"**Target:** ₹{final_plan['goal']['target']:,} | **Time Horizon:** {final_plan['goal']['horizon']} years")
    st.markdown(f"**Risk Profile:** {user_persona['risk_profile']}")

    st.subheader("📊 Curated Product Suggestions")
    
    if user_persona['risk_profile'] == "Aggressive":
        st.info("Based on your profile, here are some high-growth investment suggestions:")
        st.markdown("- **Mutual Funds:** Aggressive Equity Funds (e.g., Small Cap, Sectoral Funds)")
        st.markdown("- **Stocks:** High-growth stocks in emerging sectors (e.g., Tech, EVs)")
        st.markdown("- **AIFs:** Category III AIFs (Hedge Funds) for sophisticated investors")
    elif user_persona['risk_profile'] == "Moderate":
        st.info("Based on your profile, here are some balanced investment suggestions:")
        st.markdown("- **Mutual Funds:** Hybrid Funds, Large Cap and Mid Cap Equity Funds")
        st.markdown("- **Stocks:** Blue-chip stocks with stable growth and dividends")
        st.markdown("- **AIFs:** Category II AIFs (Private Equity, Debt Funds)")
    elif user_persona['risk_profile'] == "Moderately Conservative":
        st.info("Based on your profile, here are some moderately conservative investment suggestions:")
        st.markdown("- **Mutual Funds:** Balanced Advantage Funds, Large & Mid Cap Funds")
        st.markdown("- **Bonds:** High-rated Corporate Bonds, Dynamic Bond Funds")
        st.markdown("- **Fixed Deposits:** Laddered Fixed Deposits")
    else: # Conservative
        st.info("Based on your profile, here are some low-risk investment suggestions:")
        st.markdown("- **Mutual Funds:** Debt Funds, Index Funds, Large Cap Funds")
        st.markdown("- **Bonds:** Government Bonds, High-rated Corporate Bonds")
        st.markdown("- **Fixed Deposits:** Traditional Bank Fixed Deposits")
        
    st.subheader("📈 Your Investment Summary")
    
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Initial Investment", f"₹{final_plan['initial']:,}")
    with col2: st.metric("Monthly SIP", f"₹{final_plan['sip']:,}")
    with col3: st.metric("Portfolio Return", f"{final_plan['results']['portfolio_return']*100:.1f}%")
    
    # Time needed to reach goals calculation
    st.subheader("⏰ Time to Reach Goal")
    if final_plan['initial'] > 0 and final_plan['results']['portfolio_return'] > 0:
        years_needed = np.log(final_plan['goal']['target'] / final_plan['initial']) / np.log(1 + final_plan['results']['portfolio_return'])
        st.markdown(f"""
        <div class="info-box">
            With current allocation, you'll need approximately <strong>{years_needed:.1f} years</strong> to reach your goal.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="info-box">
            Adjust your initial investment or monthly SIP to calculate time to goal.
        </div>
        """, unsafe_allow_html=True)

    # "How much more to invest?" calculation
    st.subheader("💰 How much more to invest?")
    current_future_value = final_plan['results']['future_value']
    inflation_adjusted_target = final_plan['goal']['target'] * ((1 + 0.045) ** final_plan['goal']['horizon'])
    
    if current_future_value < inflation_adjusted_target:
        shortfall = inflation_adjusted_target - current_future_value
        remaining_horizon_months = final_plan['goal']['horizon'] * 12
        if final_plan['results']['portfolio_return'] > 0 and remaining_horizon_months > 0:
            monthly_return_rate = final_plan['results']['portfolio_return'] / 12
            if monthly_return_rate == 0:
                st.markdown("""
                <div class="info-box">
                    To calculate additional investment needed, your portfolio must have a positive return.
                </div>
                """, unsafe_allow_html=True)
            else:
                additional_monthly_needed = shortfall / (((1 + monthly_return_rate) ** remaining_horizon_months - 1) / monthly_return_rate)
                st.markdown(f"""
                <div class="info-box">
                    To reach your inflation-adjusted target of ₹{inflation_adjusted_target:,.0f}, you may need to invest an additional <strong>₹{additional_monthly_needed:,.0f} per month</strong>.
                </div>
                """, unsafe_allow_html=True)
        else:
             st.markdown("""
            <div class="info-box">
                To calculate additional investment needed, please ensure your portfolio return is positive and time horizon is set.
            </div>
            """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="success-message">
            ✅ Your current plan is projected to meet or exceed your inflation-adjusted target!
        </div>
        """, unsafe_allow_html=True)
    
    st.subheader("Professional Grade Report")
    st.markdown("""
    <div class="info-box">
    This report summarizes your financial plan, risk assessment, and recommended products.
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("📧 Generate & Email Full Report", type="primary"):
        st.success(f"Report has been successfully generated and sent to your email: {st.session_state.user_email}!")
    
    if st.button("Restart & Explore More", type="secondary"):
        st.session_state.phase = 1
        st.session_state.authenticated = False
        st.session_state.subscribed = False
        st.session_state.user_email = None
        st.session_state.final_plan = None
        st.rerun()

# --- MAIN APP LOGIC ---

def main_app():
    if st.session_state.phase == 1:
        phase_1()
    elif st.session_state.phase == 2:
        phase_2()
    elif st.session_state.phase == 3:
        if st.session_state.authenticated:
            phase_3()
        else:
            st.session_state.phase = 2
            st.rerun()
    elif st.session_state.phase == 4:
        if 'final_plan' in st.session_state and st.session_state.authenticated:
            phase_4()
        else:
            st.session_state.phase = 3
            st.rerun()
    elif st.session_state.phase == 5:
        if 'final_plan' in st.session_state and st.session_state.authenticated:
            phase_5()
        else:
            st.session_state.phase = 3
            st.rerun()
    else:
        st.session_state.phase = 1
        st.rerun()

if __name__ == "__main__":
    main_app()

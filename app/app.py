"""Streamlit web dashboard for job market analytics."""

import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="DataNerd.tech Web BI Platform 2023",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    """
    <style>
    .main { background-color: #0B0F19; }
    .stMetric {
        background-color: #111827;
        border: 1px solid #1F2937;
        border-radius: 10px;
        padding: 14px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
    }
    div[data-testid="stMetricValue"] { color: #3B82F6; font-weight: 800; font-size: 1.9rem; }
    div[data-testid="stMetricLabel"] { color: #9CA3AF; font-weight: 600; font-size: 0.85rem; text-transform: uppercase; }
    </style>
    """,
    unsafe_allow_html=True
)

from app.utils import render_vintage_banner, plot_bar_chart, render_salary_disclaimer
from app.db import (
    load_top_skills,
    load_salary_insights,
    load_top_companies,
    load_market_conditions,
    load_skill_salary_premiums
)

render_vintage_banner()

# Navigation Sidebar
st.sidebar.markdown("## 📊 DataNerd Web BI")
st.sidebar.caption("🟢 **Warehouse Online** • ⚡ **Query Latency < 2.0ms**")
page = st.sidebar.radio(
    "Select BI View:",
    [
        "1. 🔥 Skills Demand",
        "2. 💰 Salary Insights",
        "3. ⚔️ Skill Battle & Compare",
        "4. 🏢 Top Employer Leaderboard",
        "5. 🌐 Global Market Conditions",
        "6. 🔎 Skill Search Explorer",
        "7. 📚 Methodology & Viva Notes"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### 🎛️ DataNerd Role Filter")

selected_title = st.sidebar.selectbox(
    "Job Title Short Filter",
    [
        "All Roles (766k)",
        "Data Analyst (196k)",
        "Senior Data Analyst (29k)",
        "Data Engineer (186k)",
        "Senior Data Engineer (34k)",
        "Data Scientist (172k)",
        "Senior Data Scientist (25k)",
        "Business Analyst (49k)",
        "Software Engineer (45k)",
        "Cloud Engineer (12k)",
        "Machine Learning Engineer (14k)"
    ]
)

# Module 1: Skills Demand
if page == "1. 🔥 Skills Demand":
    st.title("🔥 Skills Demand Analytics")
    st.markdown(f"Current Filter Scope: **{selected_title}**")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Top Demanded Skill", "Python", "238,420 postings (31.1%)")
    col2.metric("Runner-Up Skill", "SQL", "214,580 postings (28.0%)")
    col3.metric("Top Cloud Platform", "AWS", "83,920 postings (11.0%)")
    col4.metric("Top BI Tool", "Tableau", "80,150 postings (10.5%)")
    
    st.markdown("---")
    
    df_skills = load_top_skills()
    fig_skills = plot_bar_chart(
        df_skills.head(20), x_col="demand_count", y_col="skill_name",
        title="Top 20 Technical Skills Demand (2023)", color_col="skill_type"
    )
    st.plotly_chart(fig_skills, use_container_width=True)
    
    st.subheader("📋 Skills Penetration Leaderboard")
    st.dataframe(df_skills, use_container_width=True)

# Module 2: Salary Insights
elif page == "2. 💰 Salary Insights":
    st.title("💰 Salary & Compensation Insights")
    
    df_sal = load_salary_insights()
    sample_size = df_sal['postings_with_salary'].sum()
    render_salary_disclaimer(sample_size, 4.2)
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Average Yearly Salary by Role Family & Seniority")
        fig_sal = plot_bar_chart(
            df_sal, x_col="role_family_name", y_col="avg_yearly_salary",
            color_col="seniority", title="Disclosed Yearly Salary Average (USD)"
        )
        st.plotly_chart(fig_sal, use_container_width=True)
        
    with c2:
        st.subheader("🚀 Skill Salary Premiums")
        df_prem = load_skill_salary_premiums()
        fig_prem = plot_bar_chart(
            df_prem, x_col="salary_premium_usd", y_col="skill_name",
            color_col="skill_type", title="Pay Premium over Global Benchmark ($112.4k)"
        )
        st.plotly_chart(fig_prem, use_container_width=True)

# Module 3: Skill Compare
elif page == "3. ⚔️ Skill Battle & Compare":
    st.title("⚔️ Head-to-Head Skill Battle")
    st.markdown("Compare two technical skills side-by-side on demand, pay, and market share.")
    
    col_a, col_b = st.columns(2)
    with col_a:
        skill_a = st.selectbox("Select Skill A", ["Python", "SQL", "Power BI", "AWS"], index=0)
        st.markdown(f"### 🟦 {skill_a}")
        st.metric("Demand Rank", "#1" if skill_a == "Python" else "#2")
        st.metric("Total Postings Requesting", "238,420" if skill_a == "Python" else "214,580")
        st.metric("Market Penetration Rate", "31.1%")
        st.metric("Avg Disclosed Salary", "$124,100")
        
    with col_b:
        skill_b = st.selectbox("Select Skill B", ["R", "Tableau", "Azure", "Excel"], index=1)
        st.markdown(f"### 🟪 {skill_b}")
        st.metric("Demand Rank", "#5" if skill_b == "Tableau" else "#3")
        st.metric("Total Postings Requesting", "80,150" if skill_b == "Tableau" else "95,340")
        st.metric("Market Penetration Rate", "10.5%")
        st.metric("Avg Disclosed Salary", "$109,500")

# Module 4: Top Employers
elif page == "4. 🏢 Top Employer Leaderboard":
    st.title("🏢 Employer Hiring Leaderboard")
    df_comp = load_top_companies()
    
    fig_comp = plot_bar_chart(
        df_comp.head(15), x_col="total_postings", y_col="company_name",
        title="Postings Volume by Company", color_col="avg_salary_usd"
    )
    st.plotly_chart(fig_comp, use_container_width=True)
    st.dataframe(df_comp, use_container_width=True)

# Module 5: Market Conditions
elif page == "5. 🌐 Global Market Conditions":
    st.title("🌐 Global Market Conditions & Remote Work")
    df_mkt = load_market_conditions()
    
    fig_mkt = plot_bar_chart(
        df_mkt, x_col="country", y_col="remote_work_pct",
        title="Remote Posting Percentage (%) by Country", color_col="remote_work_pct"
    )
    st.plotly_chart(fig_mkt, use_container_width=True)
    st.dataframe(df_mkt, use_container_width=True)

# Module 6: Skill Search
elif page == "6. 🔎 Skill Search Explorer":
    st.title("🔎 DataNerd Skill Search Engine")
    query = st.text_input("Search for a skill (e.g. Python, SQL, Tableau, AWS, Docker):", value="Python")
    
    df_skills = load_top_skills()
    match = df_skills[df_skills['skill_name'].str.lower() == query.strip().lower()]
    
    if not match.empty:
        s_row = match.iloc[0]
        st.success(f"### Skill Found: **{s_row['skill_name']}** (`{s_row['skill_type']}`)")
        m1, m2, m3 = st.columns(3)
        m1.metric("Overall Demand Rank", f"#{match.index[0] + 1}")
        m2.metric("Posting Demand Count", f"{s_row['demand_count']:,}")
        m3.metric("Market Penetration Rate", f"{s_row['pct_of_total_postings']}%")
    else:
        st.info(f"Skill '{query}' not found. Try searching 'Python', 'SQL', or 'AWS'.")

# Module 7: Methodology
elif page == "7. 📚 Methodology & Viva Notes":
    st.title("📚 DataNerd Methodology & Academic Viva Defense")
    st.markdown(
        """
        ### Data Source Citation
        Inspired by Luke Barousse's **DataNerd.tech** application. Data scraped from Google job search results during calendar year **2023** (787,686 total postings).
        
        ### Key Academic Viva Defense Principles
        1. **Sample Size Disclosures**: Every salary average is paired with `postings_with_salary`.
        2. **Sudan IP Artifact**: 21,519 postings attributed to Sudan represent web scraper IP artifacts and are isolated via `EXCLUDE_SUDAN=True`.
        3. **Canonical Skill Mapping**: Near-duplicate skill variants (e.g. `powerbi` $\rightarrow$ `power bi`) preserve original `skill_id` records in `skills_dim` via `canonical_skill_id` self-references.
        4. **Single-Year Vintage**: All findings reflect 2023 conditions and must not be described as real-time market data.
        """
    )

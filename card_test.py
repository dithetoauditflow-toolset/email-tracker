import streamlit as st

st.set_page_config(page_title="Client Status Dashboard", layout="wide")

# --- Sample data ---
cards = [
    {
        "name": "Bedroomania",
        "uif": "2517189/1",
        "email": "athinistofile@gmail.com",
        "sent": 6,
        "replies": 0,
        "last_contact": "2025-10-31",
        "status": "Compliant"
    },
    {
        "name": "Comien van Zyl Arbeidsterapeute",
        "uif": "2561702/8",
        "email": "chantell@maritzconsulting.co.za",
        "sent": 0,
        "replies": 0,
        "last_contact": "—",
        "status": "Compliant"
    },
    {
        "name": "DE PLAAS GUEST HOUSE",
        "uif": "2540287/2",
        "email": "reception@deplaas.co.za",
        "sent": 0,
        "replies": 0,
        "last_contact": "—",
        "status": "Compliant"
    },
    {
        "name": "DESAI ELECTRICAL WHOLESALERS",
        "uif": "2485781/9",
        "email": "beyers@imxaccounting.co.za",
        "sent": 3,
        "replies": 1,
        "last_contact": "2025-10-28",
        "status": "Compliant"
    },
    {
        "name": "Dial a Auto",
        "uif": "1811764/2",
        "email": "riaan@connix.co.za",
        "sent": 8,
        "replies": 0,
        "last_contact": "2025-10-31",
        "status": "Compliant"
    },
    {
        "name": "Griffin Consulting",
        "uif": "2455400/8",
        "email": "kim@ehlersattorneys.co.za",
        "sent": 1,
        "replies": 0,
        "last_contact": "2025-10-03",
        "status": "Compliant"
    }
]

# --- Styling ---
st.markdown("""
<style>
.card {
    background-color: white;
    border-radius: 14px;
    padding: 1.2rem 1.5rem;
    box-shadow: 0 2px 10px rgba(0,0,0,0.05);
    transition: all 0.2s ease-in-out;
    border: 1px solid #f0f0f0;
    height: 100%;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 14px rgba(0,0,0,0.08);
}
.card-title {
    font-weight: 700;
    font-size: 1.1rem;
    color: #262730;
    margin-bottom: 0.3rem;
}
.card-subtext {
    color: #5a5a5a;
    font-size: 0.9rem;
    margin-bottom: 0.5rem;
}
.card-stats {
    display: flex;
    justify-content: space-between;
    margin-top: 1rem;
}
.stat-block {
    text-align: center;
    flex: 1;
}
.stat-value {
    font-size: 1.4rem;
    font-weight: 600;
    color: #222;
}
.stat-label {
    font-size: 0.8rem;
    color: #777;
}
.card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 1rem;
}
.status-badge {
    background-color: #e6f4ea;
    color: #137333;
    font-size: 0.8rem;
    font-weight: 600;
    border-radius: 6px;
    padding: 4px 8px;
}
.copy-btn {
    background-color: #f1f3f4;
    color: #333;
    border: none;
    border-radius: 6px;
    padding: 4px 8px;
    cursor: pointer;
    font-size: 0.8rem;
}
.copy-btn:hover {
    background-color: #e0e0e0;
}
</style>
""", unsafe_allow_html=True)

# --- Title ---
st.markdown("## 💼 Client Communication Overview")
st.caption("Streamlined compliance status cards with modern layout.")

# --- Render cards ---
cols = st.columns(3)

for idx, card in enumerate(cards):
    with cols[idx % 3]:
        st.markdown(f"""
        <div class="card">
            <div>
                <div class="card-title">{card['name']}</div>
                <div class="card-subtext">
                    <b>UIF Ref:</b> {card['uif']}<br>
                    <a href="mailto:{card['email']}" style="color:#1a73e8;">{card['email']}</a>
                </div>
                <div class="card-stats">
                    <div class="stat-block">
                        <div class="stat-value">{card['sent']}</div>
                        <div class="stat-label">Sent</div>
                    </div>
                    <div class="stat-block">
                        <div class="stat-value">{card['replies']}</div>
                        <div class="stat-label">Replies</div>
                    </div>
                </div>
                <div class="card-subtext" style="margin-top:1rem;">
                    <b>Last Contact:</b> {card['last_contact']}
                </div>
            </div>
            <div class="card-footer">
                <span class="status-badge">{card['status']}</span>
                <button class="copy-btn">Copy UIF</button>
            </div>
        </div>
        """, unsafe_allow_html=True)

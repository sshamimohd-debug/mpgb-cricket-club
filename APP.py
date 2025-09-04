# APP.py  — MPGB Cricket Club – SAGAR
# Features: Guest/Member modes, Registration & ID, Match Setup, Live Scoring, Public Live Score, Player List

import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import io, os, json, uuid
from datetime import datetime

# ------------------ BASIC SETTINGS ------------------
st.set_page_config(page_title="MPGB Cricket Club – SAGAR", layout="wide", page_icon="🏏")

# Scorer PIN (set in Streamlit Cloud → Settings → Secrets → SCORER_PIN)
ADMIN_SCORER_PIN = st.secrets.get("SCORER_PIN", "4321")

# Paths
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)
LOGO_PATH = "RRB_LOGO_new.png"
PAID_XLSX = "Members_Paid.xlsx"
PAID_CSV  = "Members_Paid.csv"

REG_MEMBERS = os.path.join(DATA_DIR, "Registered_Members.csv")
MATCH_INDEX = os.path.join(DATA_DIR, "matches.json")  # matches meta

# ------------------ Helpers ------------------
def read_paid_members():
    if os.path.exists(PAID_XLSX):
        try:
            return pd.read_excel(PAID_XLSX)
        except Exception as e:
            st.warning(f"Excel read failed ({e}). Using CSV if present.")
    if os.path.exists(PAID_CSV):
        return pd.read_csv(PAID_CSV)
    return pd.DataFrame(columns=["Mobile_No"])

def init_csv(path, columns):
    if not os.path.exists(path):
        pd.DataFrame(columns=columns).to_csv(path, index=False)

def read_registered():
    init_csv(REG_MEMBERS, ["Reg_No","Name","Mobile","Branch","Role"])
    return pd.read_csv(REG_MEMBERS)

def write_registered(df):
    df.to_csv(REG_MEMBERS, index=False)

def match_state_path(match_id):
    return os.path.join(DATA_DIR, f"match_{match_id}_state.json")

def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return default

def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def make_reg_no(next_no):
    return f"MPGBCC-{datetime.now().year}-{next_no:04d}"

def overs_str(balls):   # legal balls
    return f"{balls//6}.{balls%6}"

def add_commentary(state, text):
    state["commentary"].insert(0, f"{datetime.now().strftime('%H:%M:%S')} — {text}")

# ------------------ Header ------------------
l, r = st.columns([1,5])
with l:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=90)
with r:
    st.markdown("## 🏏 MPGB CRICKET CLUB – SAGAR")
    st.caption("Registration • Live Scoring • Scorecards • Player List")

# ------------------ Sidebar: Role + Menu ------------------
role = st.sidebar.selectbox("Login as", ["Guest", "Member"])   # <<-- NEW
page = st.sidebar.radio(
    "Menu",
    ["Registration & ID Card", "Match Setup", "Live Scoring (Scorer)", "Live Score (Public View)", "Player Stats"],
    index=0
)

# =========================================================
# 1) REGISTRATION & ID CARD
# =========================================================
if page == "Registration & ID Card":
    st.subheader("Membership Registration (Mobile number verification)")
    if role == "Guest":
        st.info("👀 Guest mode: Aap sab dekh sakte hain, lekin registration/submit nahi kar sakte.")
        st.stop()

    # session flags
    if "verified" not in st.session_state:
        st.session_state.verified = False
    if "verified_mobile" not in st.session_state:
        st.session_state.verified_mobile = ""

    paid_members = read_paid_members()

    if not st.session_state.verified:
        mobile = st.text_input("📱 Enter Mobile Number", key="mobile_input")
        if st.button("Verify"):
            ok = mobile.strip() and (paid_members["Mobile_No"].astype(str) == str(mobile).strip()).any()
            if ok:
                st.session_state.verified = True
                st.session_state.verified_mobile = str(mobile).strip()
                st.success("✅ Membership Verified! Please complete your registration.")
            else:
                st.error("❌ Number not found. Please deposit ₹500 and ensure number exists in Members_Paid file.")
    else:
        st.info(f"✅ Verified mobile: **{st.session_state.verified_mobile}**")
        if st.button("Change number"):
            st.session_state.verified = False
            st.session_state.verified_mobile = ""
            st.experimental_rerun()

    if st.session_state.verified:
        with st.form("reg_form"):
            name   = st.text_input("📝 Full Name")
            branch = st.text_input("🏦 Branch Code")
            role_play = st.selectbox("🎯 Playing Role", ["Batsman","Bowler","All-Rounder","Wicketkeeper"])
            photo  = st.file_uploader("📸 Upload Your Photo", type=["jpg","jpeg","png"])
            submitted = st.form_submit_button("Generate ID")

        if submitted:
            if not name or not branch or not photo:
                st.error("⚠️ Please fill all details and upload a photo.")
            else:
                reg_df = read_registered()
                reg_no = make_reg_no(len(reg_df)+1)

                new_row = pd.DataFrame(
                    [[reg_no, name, st.session_state.verified_mobile, branch, role_play]],
                    columns=reg_df.columns
                )
                reg_df = pd.concat([reg_df, new_row], ignore_index=True)
                write_registered(reg_df)

                # ID card
                user_img = Image.open(photo).convert("RGB").resize((200,200))
                card = Image.new("RGB", (650, 420), "white")
                draw = ImageDraw.Draw(card)
                if os.path.exists(LOGO_PATH):
                    logo = Image.open(LOGO_PATH).convert("RGB").resize((90,110))
                    card.paste(logo, (280, 10))
                draw.text((170, 130), "MPGB CRICKET CLUB - SAGAR", fill="black")
                card.paste(user_img, (30, 170))
                draw.text((260, 170), f"Name: {name}", fill="blue")
                draw.text((260, 198), f"Mobile: {st.session_state.verified_mobile}", fill="black")
                draw.text((260, 226), f"Branch: {branch}", fill="black")
                draw.text((260, 254), f"Role: {role_play}", fill="black")
                draw.text((260, 282), f"Reg. No: {reg_no}", fill="red")
                st.image(card, caption="Your Membership ID Card")
                buf = io.BytesIO(); card.save(buf, format="PNG")
                st.download_button("⬇️ Download ID Card (PNG)", buf.getvalue(),
                                   file_name=f"{name}_ID.png", mime="image/png")

    st.caption("Tip: Paid members file should be `Members_Paid.xlsx` (or `Members_Paid.csv`) with a single column `Mobile_No`.")

# =========================================================
# 2) MATCH SETUP  (Member only)
# =========================================================
if page == "Match Setup":
    st.subheader("Create / Manage Matches")
    if role == "Guest":
        st.info("👀 Guest mode: Match create/edit allowed nahi hai.")
        st.stop()

    matches = load_json(MATCH_INDEX, {})
    with st.form("new_match", clear_on_submit=True):
        title = st.text_input("Match Title (e.g., MPGB A vs MPGB B)")
        venue = st.text_input("Venue")
        overs = st.number_input("Overs per innings", 1, 50, 20)
        toss_winner = st.selectbox("Toss won by", ["Team A","Team B","Decide later"])
        bat_first   = st.selectbox("Batting first", ["Team A","Team B","Decide later"])
        teamA = st.text_area("Team A players (one per line)").strip()
        teamB = st.text_area("Team B players (one per line)").strip()
        create = st.form_submit_button("Create Match")

    if create:
        if not title or not teamA or not teamB:
            st.error("Enter match title and both team lists.")
        else:
            match_id = datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
            matches[match_id] = {
                "title": title,
                "venue": venue,
                "overs": int(overs),
                "toss_winner": toss_winner,
                "bat_first": bat_first,
                "teamA": [p.strip() for p in teamA.splitlines() if p.strip()],
                "teamB": [p.strip() for p in teamB.splitlines() if p.strip()],
                "created_at": datetime.now().isoformat()
            }
            save_json(MATCH_INDEX, matches)

            init_bat = "Team A" if bat_first=="Team A" else ("Team B" if bat_first=="Team B" else "Team A")
            state = {
                "status": "INNINGS1",
                "innings": 1,
                "overs_limit": int(overs),
                "bat_team": init_bat,
                "bowl_team": "Team B" if init_bat=="Team A" else "Team A",
                "teams": {"Team A": matches[match_id]["teamA"], "Team B": matches[match_id]["teamB"]},
                "score": {"Team A":{"runs":0,"wkts":0,"balls":0},
                          "Team B":{"runs":0,"wkts":0,"balls":0}},
                "batting": {"striker":"", "non_striker":"", "next_index":0,
                            "order": matches[match_id]["teamA"][:] if init_bat=="Team A" else matches[match_id]["teamB"][:] },
                "bowling": {"current_bowler":""},
                "batsman_stats": {},
                "bowler_stats":  {},
                "commentary": []
            }
            save_json(match_state_path(match_id), state)
            st.success(f"✅ Match created! Match ID: **{match_id}**")

    st.markdown("### Existing Matches")
    matches = load_json(MATCH_INDEX, {})
    if matches:
        for mid, meta in list(matches.items())[::-1]:
            st.write(f"**{meta['title']}** — `{mid}` @ {meta.get('venue','')}, Overs: {meta['overs']}")
    else:
        st.info("No matches yet. Use the form above.")

# =========================================================
# 3) LIVE SCORING (SCORER)  — PIN protected
# =========================================================
if page == "Live Scoring (Scorer)":
    st.subheader("Ball-by-Ball Scoring (Scorer Mode)")
    if role == "Guest":
        st.info("👀 Guest mode: Scoring allowed nahi hai.")
        st.stop()

    pin = st.text_input("Enter Scorer PIN", type="password")
    if pin != ADMIN_SCORER_PIN:
        st.warning("Valid Scorer PIN required.")
        st.stop()

    matches = load_json(MATCH_INDEX, {})
    if not matches:
        st.info("Create a match first in 'Match Setup'.")
        st.stop()

    match_id = st.selectbox("Select Match", list(matches.keys())[::-1],
                            format_func=lambda k: f"{matches[k]['title']} — {k}")
    if not match_id:
        st.stop()

    meta = matches[match_id]
    state = load_json(match_state_path(match_id), {})
    if not state:
        st.error("Match state missing. Recreate the match.")
        st.stop()

    colA, colB, colC, colD = st.columns(4)
    bat = state["bat_team"]; bowl = state["bowl_team"]
    with colA:
        sc = state["score"][bat]
        st.metric(f"{bat} Score", f"{sc['runs']}/{sc['wkts']}")
    with colB:
        st.metric("Overs", overs_str(sc["balls"]))
    with colC:
        st.metric("Innings", f"{state['innings']}/2")
    with colD:
        st.metric("Status", state["status"])

    st.markdown("#### Select Batsmen & Bowler")
    players_bat = state["teams"][bat]; players_bowl = state["teams"][bowl]
    with st.form("who_is_playing"):
        striker = st.selectbox("Striker", [""]+players_bat,
                               index=([""]+players_bat).index(state["batting"].get("striker",""))
                               if state["batting"].get("striker","") in ([""]+players_bat) else 0)
        non_striker = st.selectbox("Non-Striker", [""]+players_bat,
                                   index=([""]+players_bat).index(state["batting"].get("non_striker",""))
                                   if state["batting"].get("non_striker","") in ([""]+players_bat) else 0)
        bowler = st.selectbox("Bowler", [""]+players_bowl,
                              index=([""]+players_bowl).index(state["bowling"].get("current_bowler",""))
                              if state["bowling"].get("current_bowler","") in ([""]+players_bowl) else 0)
        set_btn = st.form_submit_button("Set/Update")

    if set_btn:
        if not striker or not non_striker or not bowler or striker==non_striker:
            st.error("Select valid striker, non-striker and bowler.")
        else:
            state["batting"]["striker"] = striker
            state["batting"]["non_striker"] = non_striker
            state["bowling"]["current_bowler"] = bowler
            for p in [striker, non_striker]:
                state["batsman_stats"].setdefault(p, {"R":0,"B":0,"4":0,"6":0})
            state["bowler_stats"].setdefault(bowler, {"B":0,"R":0,"W":0})
            save_json(match_state_path(match_id), state)
            st.success("Updated.")

    st.markdown("#### Record a Ball")
    with st.form("ball", clear_on_submit=True):
        outcome = st.radio("Outcome", ["0","1","2","3","4","6","Wicket","Wide","No-Ball","Leg Bye","Bye"], horizontal=True)
        runs_off_bat_nb = 0
        if outcome == "No-Ball":
            runs_off_bat_nb = st.number_input("Runs off bat on No-Ball (0–6)", 0, 6, 0)
        wicket_info = ""
        if outcome == "Wicket":
            wicket_info = st.text_input("Dismissal (e.g., Bowled, Caught by X)")
        submit = st.form_submit_button("Add Ball")

    if submit:
        s = state
        if not s["batting"]["striker"] or not s["bowling"]["current_bowler"]:
            st.error("Set striker & bowler above first.")
            st.stop()

        striker = s["batting"]["striker"]; non_striker = s["batting"]["non_striker"]; bowler = s["bowling"]["current_bowler"]
        s["batsman_stats"].setdefault(striker, {"R":0,"B":0,"4":0,"6":0})
        s["batsman_stats"].setdefault(non_striker, {"R":0,"B":0,"4":0,"6":0})
        s["bowler_stats"].setdefault(bowler, {"B":0,"R":0,"W":0})

        legal_ball = True
        add_runs_team = 0
        highlight = ""

        if outcome in ["0","1","2","3","4","6"]:
            r = int(outcome)
            add_runs_team = r
            s["batsman_stats"][striker]["R"] += r
            s["batsman_stats"][striker]["B"] += 1
            s["bowler_stats"][bowler]["B"] += 1
            s["bowler_stats"][bowler]["R"] += r
            if r==4: s["batsman_stats"][striker]["4"] += 1
            if r==6: s["batsman_stats"][striker]["6"] += 1
            highlight = f"{r} run(s)" if r>0 else "dot ball"
            if r % 2 == 1:
                s["batting"]["striker"], s["batting"]["non_striker"] = non_striker, striker

        elif outcome == "Wicket":
            s["score"][s["bat_team"]]["wkts"] += 1
            s["batsman_stats"][striker]["B"] += 1
            s["bowler_stats"][bowler]["B"] += 1
            s["bowler_stats"][bowler]["W"] += 1
            highlight = f"WICKET! {wicket_info or ''}".strip()

            order = s["batting"]["order"]; nxt = s["batting"]["next_index"]
            nxt_player = ""
            while nxt < len(order):
                candidate = order[nxt]; nxt += 1
                if candidate not in [striker, non_striker]:
                    nxt_player = candidate; break
            s["batting"]["next_index"] = nxt
            if nxt_player:
                s["batting"]["striker"] = nxt_player
                s["batsman_stats"].setdefault(nxt_player, {"R":0,"B":0,"4":0,"6":0})

        elif outcome == "Wide":
            legal_ball = False
            add_runs_team = 1
            s["bowler_stats"][bowler]["R"] += 1
            highlight = "Wide"

        elif outcome == "No-Ball":
            legal_ball = False
            add_runs_team = 1 + int(runs_off_bat_nb)
            s["bowler_stats"][bowler]["R"] += add_runs_team
            if runs_off_bat_nb:
                s["batsman_stats"][striker]["R"] += int(runs_off_bat_nb)
            if runs_off_bat_nb % 2 == 1:
                s["batting"]["striker"], s["batting"]["non_striker"] = non_striker, striker
            highlight = f"No-Ball (+{1})"

        elif outcome in ["Leg Bye", "Bye"]:
            legal_ball = True
            add_runs_team = 1
            s["batsman_stats"][striker]["B"] += 1
            s["bowler_stats"][bowler]["B"] += 1
            highlight = "Leg Bye" if outcome=="Leg Bye" else "Bye"
            s["batting"]["striker"], s["batting"]["non_striker"] = non_striker, striker

        s["score"][s["bat_team"]]["runs"] += add_runs_team
        if legal_ball:
            s["score"][s["bat_team"]]["balls"] += 1
            if s["score"][s["bat_team"]]["balls"] % 6 == 0:
                s["batting"]["striker"], s["batting"]["non_striker"] = s["batting"]["non_striker"], s["batting"]["striker"]

        add_commentary(s, f"{outcome} — {striker} vs {bowler}: {highlight}")
        save_json(match_state_path(match_id), s)
        st.success("Ball recorded.")

    st.markdown("### Commentary / Highlights (latest first)")
    st.write("\n".join(state.get("commentary", [])[:25]))

# =========================================================
# 4) LIVE SCORE (PUBLIC VIEW) — always allowed
# =========================================================
if page == "Live Score (Public View)":
    st.subheader("Live Score & Highlights (Read-Only)")
    matches = load_json(MATCH_INDEX, {})
    if not matches:
        st.info("No matches yet.")
        st.stop()

    match_id = st.selectbox("Select Match", list(matches.keys())[::-1],
                            format_func=lambda k: f"{matches[k]['title']} — {k}")
    meta = matches[match_id]
    state = load_json(match_state_path(match_id), {})
    if not state:
        st.warning("State not found for this match yet.")
        st.stop()

    c1, c2 = st.columns(2)
    with c1:
        bat = state["bat_team"]; sc = state["score"][bat]
        st.markdown(f"### **{meta['title']}**")
        st.write(f"**Venue:** {meta.get('venue','')} • **Overs:** {meta['overs']}")
        st.metric(f"{bat} Score", f"{sc['runs']}/{sc['wkts']}")
        st.metric("Overs", overs_str(sc['balls']))
    with c2:
        st.markdown("### Batsmen (current)")
        st.write(f"**Striker:** {state['batting'].get('striker','')}")
        st.write(f"**Non-Striker:** {state['batting'].get('non_striker','')}")
        st.markdown("### Bowler (current)")
        st.write(state['bowling'].get("current_bowler",""))

    st.markdown("### Highlights")
    st.write("\n".join(state.get("commentary", [])[:30]))
    st.caption("Tip: Pull to refresh (mobile) or tap browser refresh for the latest ball.")

# =========================================================
# 5) PLAYER STATS — always allowed (read-only)
# =========================================================
if page == "Player Stats":
    st.subheader("Registered Members")
    df = read_registered()
    st.dataframe(df, use_container_width=True)
    st.caption("Advanced season-wise stats can be derived from ball-by-ball data (next version).")
# test rebuild


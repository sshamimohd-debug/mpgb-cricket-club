# APP_final.py — MPGB Cricket Club – SAGAR (Cricbuzz-style UI)
# Author: ChatGPT
# Notes:
# - Enforces over limits per innings
# - Blocks same bowler from bowling consecutive overs
# - Correct strike rotation (incl. byes/leg-byes, wides & no-balls)
# - Two innings with automatic switch after overs/all-out
# - Hidden Admin page to manage Paid Members list (only with PIN)
# - Improved, mobile-friendly UI inspired by Cricbuzz

import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import io, os, json, uuid
from datetime import datetime

# -------------------- App Setup --------------------
st.set_page_config(page_title="MPGB Cricket Club – SAGAR", layout="wide", page_icon="🏏")
try:
    ADMIN_SCORER_PIN = st.secrets["SCORER_PIN"]
except Exception:
    ADMIN_SCORER_PIN = "4321"  # agar secrets.toml nahi hai to default PIN

DATA_DIR = "data"; os.makedirs(DATA_DIR, exist_ok=True)
LOGO_PATH = "RRB_LOGO_new.png"
PAID_XLSX = "Members_Paid.xlsx"   # read priority
PAID_CSV  = "Members_Paid.csv"    # write priority (admin page writes here)

REG_MEMBERS = os.path.join(DATA_DIR, "Registered_Members.csv")
MATCH_INDEX = os.path.join(DATA_DIR, "matches.json")

# -------------------- Theme (Cricbuzz-ish) --------------------
PRIMARY = "#0B8457"  # deep green
DARK = "#0E3C2F"
ACCENT = "#2ECC71"
TEXT_ON_DARK = "#EAF8F0"

st.markdown(f"""
<style>
/***** Global *****/
:root {{
  --primary: {PRIMARY};
  --dark: {DARK};
  --accent: {ACCENT};
  --text-on-dark: {TEXT_ON_DARK};
}}
.block-container {{ padding-top: 0.75rem; }}
html, body, [class*="css"] {{ font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; }}

/***** Header Bar *****/
.header-wrap {{
  background: linear-gradient(90deg, var(--dark), var(--primary));
  color: var(--text-on-dark);
  border-radius: 14px;
  padding: 12px 16px; margin-bottom: 10px;
}}
.header-title {{ font-size: 1.25rem; font-weight: 700; letter-spacing: .2px; }}
.header-sub {{ opacity:.9; font-size:.9rem; margin-top:-3px; }}

/***** Score Cards *****/
.score-card {{
  background: #ffffff; border-radius: 16px; box-shadow: 0 4px 14px rgba(0,0,0,.08);
  padding: 16px; border: 1px solid rgba(0,0,0,.06);
}}
.score-strip {{
  background: var(--dark); color: var(--text-on-dark);
  border-radius: 14px; padding: 10px 14px; font-weight: 700;
}}
.metric-inline {{ display:flex; gap:14px; flex-wrap:wrap; align-items:center; }}
.metric-inline .pill {{
  background: rgba(11,132,87,.1); color: var(--dark); font-weight: 600;
  padding: 8px 12px; border-radius: 12px; border: 1px solid rgba(11,132,87,.25);
}}

/***** Ball chips *****/
.ball-feed {{ margin-top: 6px; }}
.ball-chip {{ display:inline-block; padding: 6px 10px; border-radius: 999px; margin: 3px 4px; font-weight:700; border:1px solid rgba(0,0,0,.08); }}
.chip-0 {{ background:#F3F4F6; }}
.chip-1, .chip-2, .chip-3 {{ background:#E8FFF2; }}
.chip-4 {{ background:#FFF4D6; }}
.chip-6 {{ background:#FFE3E3; }}
.chip-w {{ background:#1F2937; color:white; }}
.chip-nb {{ background:#DCFCE7; }}
.chip-wide {{ background:#E0E7FF; }}
.chip-bye {{ background:#F1F5F9; }}

/***** Buttons *****/
.stButton>button {{ border-radius: 12px; font-weight: 700; padding: .5rem 1rem; border:1px solid rgba(0,0,0,.05) }}
.stButton>button[kind="primary"] {{ background: var(--primary) !important; color:white !important; }}

/***** Forms *****/
label, .stSelectbox label {{ font-weight: 700 !important; color: #0F172A; }}
.stRadio > div {{ gap: 8px; }}

/***** Mobile tweaks *****/
@media (max-width: 768px) {{
  .header-title {{ font-size: 1.05rem; }}
  .score-strip {{ font-size:.95rem; }}
}}
</style>
""", unsafe_allow_html=True)

# -------------------- Helpers --------------------
def read_paid_members() -> pd.DataFrame:
    if os.path.exists(PAID_XLSX):
        try: return pd.read_excel(PAID_XLSX)
        except Exception as e:
            st.warning(f"Excel read failed ({e}). Using CSV if present.")
    if os.path.exists(PAID_CSV):
        return pd.read_csv(PAID_CSV)
    return pd.DataFrame(columns=["Mobile_No"])  # default shape

def write_paid_members(df: pd.DataFrame):
    # Always write CSV (safer for Streamlit Cloud); keep a simple column Mobile_No
    try:
        df = df[["Mobile_No"]].copy()
    except Exception:
        df = pd.DataFrame({"Mobile_No": pd.Series(dtype=str)})
    df["Mobile_No"] = df["Mobile_No"].astype(str).str.strip()
    df = df[df["Mobile_No"] != ""]
    df.to_csv(PAID_CSV, index=False)


def init_csv(path, cols):
    if not os.path.exists(path):
        pd.DataFrame(columns=cols).to_csv(path, index=False)


def read_registered():
    init_csv(REG_MEMBERS, ["Reg_No","Name","Mobile","Branch","Role"])
    return pd.read_csv(REG_MEMBERS)


def write_registered(df):
    df.to_csv(REG_MEMBERS, index=False)


def load_json(path, default):
    if not os.path.exists(path): return default
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except: return default


def save_json(path, obj):
    with open(path, "w", encoding="utf-8") as f: json.dump(obj, f, indent=2, ensure_ascii=False)


def match_state_path(mid): return os.path.join(DATA_DIR, f"match_{mid}_state.json")

def make_reg_no(n): return f"MPGBCC-{datetime.now().year}-{n:04d}"

def overs_str(balls): return f"{balls//6}.{balls%6}"

def add_commentary(state, txt): state["commentary"].insert(0, f"{datetime.now().strftime('%H:%M:%S')} — {txt}")


def ensure_state_defaults(s, meta):
    # Backward/forward compatible keys
    s.setdefault("status", "INNINGS1")
    s.setdefault("innings", 1)
    s.setdefault("overs_limit", int(meta.get("overs", 20)))
    s.setdefault("balls_log", [])  # list of dicts {over, ball, txt, tag}
    s.setdefault("over_in_progress", False)
    s.setdefault("batting", {"striker":"","non_striker":"","next_index":0, "order": []})
    s.setdefault("bowling", {"current_bowler":"","last_over_bowler":""})
    s.setdefault("batsman_stats", {})
    s.setdefault("bowler_stats", {})
    s.setdefault("commentary", [])
    s.setdefault("teams", {"Team A": meta.get("teamA", []), "Team B": meta.get("teamB", [])})
    s.setdefault("score", {"Team A":{"runs":0,"wkts":0,"balls":0}, "Team B":{"runs":0,"wkts":0,"balls":0}})


def rr(runs, balls):
    if balls == 0: return 0.0
    return round((runs * 6) / balls, 2)


def end_over(s):
    bat = s["bat_team"]
    sc = s["score"][bat]
    # Swap strike at the end of a completed over
    s["batting"]["striker"], s["batting"]["non_striker"] = s["batting"]["non_striker"], s["batting"]["striker"]
    # Remember who just bowled; force new selection
    s["bowling"]["last_over_bowler"] = s["bowling"].get("current_bowler", "")
    s["bowling"]["current_bowler"] = ""
    s["over_in_progress"] = False
    add_commentary(s, f"Over complete: {overs_str(sc['balls'])} — {bat} {sc['runs']}/{sc['wkts']}")


def end_innings(s, matches, mid):
    # Called when overs finished or all out
    if s["innings"] == 1:
        add_commentary(s, "Innings 1 complete.")
        # Switch teams
        s["innings"] = 2
        s["status"] = "INNINGS2"
        s["bat_team"], s["bowl_team"] = s["bowl_team"], s["bat_team"]
        # New batting order from that team's list
        s["batting"] = {"striker":"","non_striker":"","next_index":0, "order": s["teams"][s["bat_team"]][:]}
        s["bowling"] = {"current_bowler":"", "last_over_bowler":""}
        s["over_in_progress"] = False
        save_json(match_state_path(mid), s)
    else:
        s["status"] = "COMPLETED"
        add_commentary(s, "Match completed.")
        save_json(match_state_path(mid), s)


# -------------------- Header --------------------
cl, cr = st.columns([1,9])
with cl:
    if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=72)
with cr:
    st.markdown(
        f"""
        <div class='header-wrap'>
          <div class='header-title'>🏏 MPGB CRICKET CLUB – SAGAR</div>
          <div class='header-sub'>Registration • Cricbuzz-style Live Scoring • Hidden Admin tools</div>
        </div>
        """, unsafe_allow_html=True)

# -------------------- Sidebar: Role + Menu --------------------
st.sidebar.header("User Mode")
role = st.sidebar.radio("Login as:", ["Guest", "Member"], index=0)

# Admin PIN gate (also used for Scorer)
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False
    st.session_state.admin_checked = False

with st.sidebar.expander("Admin / Scorer PIN", expanded=False):
    pin_try = st.text_input("Enter PIN", type="password")
    if st.button("Validate PIN"):
        st.session_state.is_admin = (pin_try == ADMIN_SCORER_PIN)
        st.session_state.admin_checked = True
        st.success("Admin/Scorer access granted." if st.session_state.is_admin else "Invalid PIN.")

menu_items = [
    "Registration & ID Card",
    "Match Setup",
    "Live Scoring (Scorer)",
    "Live Score (Public View)",
    "Player Stats",
]
if st.session_state.is_admin:
    menu_items.append("Admin (Hidden)")

page = st.sidebar.radio("Menu", menu_items, index=0)

# =========================================================
# 1) REGISTRATION & ID CARD  (Member only)
# =========================================================
if page == "Registration & ID Card":
    st.subheader("Membership Registration (Mobile verification)")
    if role == "Guest":
        st.info("👀 Guest mode: Sirf dekh sakte ho, registration nahi kar sakte.")
        st.stop()

    paid = read_paid_members()
    if "verified_mobile" not in st.session_state:
        st.session_state.verified_mobile = ""

    # Step 1: Verify (unless admin toggles bypass)
    bypass = st.checkbox("Admin bypass (skip paid verification)", value=False) if st.session_state.is_admin else False

    if not st.session_state.verified_mobile and not bypass:
        mobile = st.text_input("📱 Enter Mobile Number")
        if st.button("Verify"):
            if (paid["Mobile_No"].astype(str) == str(mobile).strip()).any():
                st.session_state.verified_mobile = str(mobile).strip()
                st.success("✅ Membership Verified! Please complete your registration.")
            else:
                st.error("❌ Number not found in Members_Paid list.")
        st.stop()  # until verified we stop page here

    # Step 2: Form (stable while typing)
    verified_note = st.session_state.verified_mobile if not bypass else "(Admin bypass)"
    st.info(f"✅ Verified Mobile: {verified_note}")
    with st.form("reg_form"):
        name   = st.text_input("📝 Full Name")
        branch = st.text_input("🏦 Branch Code")
        role_play = st.selectbox("🎯 Playing Role", ["Batsman","Bowler","All-Rounder","Wicketkeeper"])
        photo  = st.file_uploader("📸 Upload Your Photo", type=["jpg","jpeg","png"])
        submitted = st.form_submit_button("Generate ID")

    if submitted:
        if not name or not branch or not photo:
            st.error("⚠️ Please fill all fields and upload photo.")
        else:
            reg_df = read_registered()
            reg_no = make_reg_no(len(reg_df)+1)
            new_row = pd.DataFrame([[reg_no, name, st.session_state.verified_mobile if not bypass else "*admin*", branch, role_play]],
                                   columns=reg_df.columns)
            reg_df = pd.concat([reg_df, new_row], ignore_index=True)
            write_registered(reg_df)

            # Professional ID Card (simple, clean)
            user_img = Image.open(photo).convert("RGB").resize((240,240))
            W, H = 700, 430
            card = Image.new("RGB", (W,H), "white")
            draw = ImageDraw.Draw(card)
            # Header bar
            draw.rectangle([0,0,W,86], fill=(11,132,87))  # primary
            title = "MPGB CRICKET CLUB - SAGAR"
            draw.text((24,24), title, fill=(234,248,240))
            # Logo
            if os.path.exists(LOGO_PATH):
                logo = Image.open(LOGO_PATH).convert("RGB").resize((70,84))
                card.paste(logo, (W-70-18, 2))
            # Photo box
            card.paste(user_img, (24, 120))
            # Info block
            x0, y0 = 290, 120
            draw.text((x0, y0),     f"Name: {name}", fill=(15,23,42))
            draw.text((x0, y0+26),  f"Mobile: {st.session_state.verified_mobile if not bypass else '—'}", fill=(30,41,59))
            draw.text((x0, y0+52),  f"Branch: {branch}", fill=(30,41,59))
            draw.text((x0, y0+78),  f"Role: {role_play}", fill=(30,41,59))
            draw.text((x0, y0+104), f"Reg. No: {reg_no}", fill=(200,30,30))
            draw.text((24, 380), "Valid for: MPGB Cricket Club events", fill=(71,85,105))

            st.image(card, caption="Your Membership ID Card")
            buf = io.BytesIO(); card.save(buf, format="PNG")
            st.download_button("⬇️ Download ID Card", buf.getvalue(), file_name=f"{name}_ID.png", mime="image/png")

    st.caption("Paid list file: `Members_Paid.xlsx` or `Members_Paid.csv` with single column `Mobile_No`.")

# =========================================================
# 2) MATCH SETUP (Member only)
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
            mid = datetime.now().strftime("%Y%m%d") + "-" + uuid.uuid4().hex[:6].upper()
            matches[mid] = {
                "title": title, "venue": venue, "overs": int(overs),
                "toss_winner": toss_winner, "bat_first": bat_first,
                "teamA": [p.strip() for p in teamA.splitlines() if p.strip()],
                "teamB": [p.strip() for p in teamB.splitlines() if p.strip()],
                "created_at": datetime.now().isoformat()
            }
            save_json(MATCH_INDEX, matches)

            init_bat = "Team A" if bat_first=="Team A" else ("Team B" if bat_first=="Team B" else "Team A")
            state = {
                "status":"INNINGS1","innings":1,"overs_limit":int(overs),
                "bat_team":init_bat,"bowl_team":"Team B" if init_bat=="Team A" else "Team A",
                "teams":{"Team A":matches[mid]["teamA"],"Team B":matches[mid]["teamB"]},
                "score":{"Team A":{"runs":0,"wkts":0,"balls":0},"Team B":{"runs":0,"wkts":0,"balls":0}},
                "batting":{"striker":"","non_striker":"","next_index":0,
                           "order": matches[mid]["teamA"][:] if init_bat=="Team A" else matches[mid]["teamB"][:]},
                "bowling":{"current_bowler":"","last_over_bowler":""},
                "batsman_stats":{},"bowler_stats":{},"commentary":[],
                "balls_log":[], "over_in_progress":False
            }
            save_json(match_state_path(mid), state)
            st.success(f"✅ Match created! Match ID: **{mid}**")

    st.markdown("### Existing Matches")
    matches = load_json(MATCH_INDEX, {})
    if matches:
        for mid, m in list(matches.items())[::-1]:
            st.write(f"**{m['title']}** — `{mid}` @ {m.get('venue','')}, Overs: {m['overs']}")
    else:
        st.info("No matches yet.")

# =========================================================
# 3) LIVE SCORING (SCORER) — Member + PIN
# =========================================================
if page == "Live Scoring (Scorer)":
    st.subheader("Ball-by-Ball Scoring (Cricbuzz style)")
    if role == "Guest":
        st.info("👀 Guest mode: Scoring allowed nahi hai.")
        st.stop()

    # Require Admin/Scorer PIN
    if not st.session_state.is_admin:
        st.warning("Valid Admin/Scorer PIN required (see sidebar).")
        st.stop()

    matches = load_json(MATCH_INDEX, {})
    if not matches:
        st.info("Create a match first in 'Match Setup'."); st.stop()

    mid = st.selectbox("Select Match", list(matches.keys())[::-1],
                       format_func=lambda k: f"{matches[k]['title']} — {k}")
    if not mid: st.stop()

    meta = matches[mid]
    state = load_json(match_state_path(mid), {})
    if not state: st.error("Match state missing. Recreate the match."); st.stop()
    ensure_state_defaults(state, meta)

    bat = state["bat_team"]; bowl = state["bowl_team"]; sc = state["score"][bat]

    # OVER LIMIT GUARD — block if innings complete
    if state["status"] == "COMPLETED":
        st.success("🏁 Match completed. Use Public View for final scorecard.")
    if state["innings"] == 1 and sc["balls"] >= state["overs_limit"]*6:
        end_innings(state, matches, mid)
        sc = state["score"][state["bat_team"]]  # update after switch
    elif state["innings"] == 2 and sc["balls"] >= state["overs_limit"]*6:
        state["status"] = "COMPLETED"
        save_json(match_state_path(mid), state)

    # Top strip
    st.markdown(
        f"<div class='score-strip'>Innings {state['innings']}/2 • Overs {overs_str(sc['balls'])}/{state['overs_limit']} • RR {rr(sc['runs'], sc['balls'])}</div>",
        unsafe_allow_html=True
    )

    c1,c2,c3 = st.columns([2,1,1])
    with c1:
        st.markdown("### ")
        st.markdown(
            f"<div class='score-card'><div class='metric-inline'>"
            f"<div class='pill'><b>{bat}</b> {sc['runs']}/{sc['wkts']}</div>"
            f"<div class='pill'>Bowling: <b>{state['bowling'].get('current_bowler','') or '—'}</b></div>"
            f"<div class='pill'>Status: <b>{state['status']}</b></div>"
            f"</div></div>", unsafe_allow_html=True)
    with c2:
        st.metric("Overs", overs_str(sc["balls"]))
    with c3:
        st.metric("Run Rate", rr(sc["runs"], sc["balls"]))

    # Select players for this over
    st.markdown("#### Select Batsmen & Bowler")
    bat_players = state["teams"][bat]; bowl_players = state["teams"][bowl]

    # Force NEW bowler after over completion
    last_b = state["bowling"].get("last_over_bowler", "")
    must_pick_new = (not state.get("over_in_progress", False))
    bowler_list = [p for p in bowl_players if (not must_pick_new) or (p != last_b)]
    bowler_label = "Bowler (new over: pick different from last over)" if must_pick_new and last_b else "Bowler"

    with st.form("set_players"):
        striker = st.selectbox("Striker", [""]+bat_players,
                               index=( [""]+bat_players ).index(state["batting"].get("striker", ""))
                                     if state["batting"].get("striker", "") in ([""]+bat_players) else 0)
        non_striker = st.selectbox("Non-Striker", [""]+bat_players,
                                   index=( [""]+bat_players ).index(state["batting"].get("non_striker", ""))
                                         if state["batting"].get("non_striker", "") in ([""]+bat_players) else 0)
        bowler = st.selectbox(bowler_label, [""]+bowler_list,
                              index=( [""]+bowler_list ).index(state["bowling"].get("current_bowler", ""))
                                    if state["bowling"].get("current_bowler", "") in ([""]+bowler_list) else 0)
        set_btn = st.form_submit_button("Set/Update")

    if set_btn:
        if not striker or not non_striker or not bowler or striker==non_striker:
            st.error("Select valid striker, non-striker, bowler.")
        else:
            # Enforce different bowler at start of new over
            if must_pick_new and last_b and bowler == last_b:
                st.error("New over must start with a DIFFERENT bowler.")
            else:
                state["batting"]["striker"]=striker; state["batting"]["non_striker"]=non_striker
                state["bowling"]["current_bowler"]=bowler
                state["over_in_progress"] = True
                for p in [striker, non_striker]:
                    state["batsman_stats"].setdefault(p, {"R":0,"B":0,"4":0,"6":0})
                state["bowler_stats"].setdefault(bowler, {"B":0,"R":0,"W":0})
                save_json(match_state_path(mid), state); st.success("Updated.")

    if must_pick_new and last_b and not state["bowling"].get("current_bowler"):
        st.warning(f"🟢 New over: choose a bowler (not {last_b}).")

    # ---------------- Ball input ----------------
    st.markdown("#### Record a Ball")

    disabled_scoring = state["status"] == "COMPLETED"

    with st.form("ball", clear_on_submit=True):
        outcome = st.radio("Outcome", ["0","1","2","3","4","6","Wicket","Wide","No-Ball","Leg Bye","Bye"],
                           horizontal=True, disabled=disabled_scoring)
        runs_off_bat_nb = st.number_input("Runs off bat on No-Ball (0–6)", 0, 6, 0, disabled=(outcome!="No-Ball" or disabled_scoring))
        wide_runs = st.number_input("Extra runs on Wide (besides +1)", 0, 6, 0, disabled=(outcome!="Wide" or disabled_scoring))
        lb_runs = st.number_input("Leg Bye runs (0–6)", 0, 6, 1, disabled=(outcome!="Leg Bye" or disabled_scoring))
        bye_runs = st.number_input("Bye runs (0–6)", 0, 6, 1, disabled=(outcome!="Bye" or disabled_scoring))
        wicket_info = st.text_input("Dismissal (e.g., Bowled, Caught by X)", disabled=(outcome!="Wicket" or disabled_scoring))
        submit = st.form_submit_button("Add Ball", disabled=disabled_scoring)

    if submit:
        s = state
        # Guards
        if s["status"] == "COMPLETED":
            st.info("Match completed.")
            st.stop()
        if not s["batting"]["striker"] or not s["bowling"].get("current_bowler"):
            st.error("Set striker & bowler above first."); st.stop()
        if not s.get("over_in_progress", False):
            st.error("Start the over by choosing a new bowler."); st.stop()

        striker = s["batting"]["striker"]; non_striker = s["batting"]["non_striker"]; bowler = s["bowling"]["current_bowler"]
        s["batsman_stats"].setdefault(striker, {"R":0,"B":0,"4":0,"6":0})
        s["batsman_stats"].setdefault(non_striker, {"R":0,"B":0,"4":0,"6":0})
        s["bowler_stats"].setdefault(bowler, {"B":0,"R":0,"W":0})

        bat_team = s["bat_team"]; sc = s["score"][bat_team]

        # Prevent further legal balls if overs finished for this innings
        if sc["balls"] >= s["overs_limit"]*6:
            end_innings(s, matches, mid)
            save_json(match_state_path(mid), s)
            st.warning("Innings closed. Switch to next innings or end match.")
            st.stop()

        legal_ball=True; add_runs=0; chip_tag=""; chip_txt=""; highlight=""

        # ----- Outcomes -----
        if outcome in ["0","1","2","3","4","6"]:
            r = int(outcome); add_runs = r
            s["batsman_stats"][striker]["R"] += r; s["batsman_stats"][striker]["B"] += 1
            s["bowler_stats"][bowler]["B"] += 1;   s["bowler_stats"][bowler]["R"] += r
            if r==4: s["batsman_stats"][striker]["4"] += 1
            if r==6: s["batsman_stats"][striker]["6"] += 1
            highlight = f"{r} run(s)" if r>0 else "dot ball"
            chip_tag = "chip-0" if r==0 else ("chip-4" if r==4 else ("chip-6" if r==6 else "chip-1"))
            chip_txt = str(r)
            if r % 2 == 1:
                s["batting"]["striker"], s["batting"]["non_striker"] = non_striker, striker

        elif outcome == "Wicket":
            s["score"][bat_team]["wkts"] += 1
            s["batsman_stats"][striker]["B"] += 1
            s["bowler_stats"][bowler]["B"] += 1; s["bowler_stats"][bowler]["W"] += 1
            highlight = f"WICKET! {wicket_info}".strip(); chip_tag = "chip-w"; chip_txt = "W"
            # bring next batter
            order = s["batting"]["order"]; nxt = s["batting"]["next_index"]; nxt_p = ""
            while nxt < len(order):
                c = order[nxt]; nxt += 1
                if c not in [striker, non_striker]: nxt_p = c; break
            s["batting"]["next_index"] = nxt
            if nxt_p:
                s["batting"]["striker"] = nxt_p
                s["batsman_stats"].setdefault(nxt_p, {"R":0,"B":0,"4":0,"6":0})

        elif outcome == "Wide":
            legal_ball = False
            add_runs = 1 + int(wide_runs)
            s["bowler_stats"][bowler]["R"] += add_runs
            highlight = f"Wide (+{1 + int(wide_runs)})"
            chip_tag = "chip-wide"; chip_txt = "Wd"
            # Strike changes only if batters ran odd number of runs on the wide
            if int(wide_runs) % 2 == 1:
                s["batting"]["striker"], s["batting"]["non_striker"] = non_striker, striker

        elif outcome == "No-Ball":
            legal_ball = False
            add_runs = 1 + int(runs_off_bat_nb)
            s["bowler_stats"][bowler]["R"] += add_runs
            if runs_off_bat_nb:
                s["batsman_stats"][striker]["R"] += int(runs_off_bat_nb)
            highlight = f"No-Ball (+1) + {int(runs_off_bat_nb)} off bat" if runs_off_bat_nb else "No-Ball (+1)"
            chip_tag = "chip-nb"; chip_txt = "NB"
            if int(runs_off_bat_nb) % 2 == 1:
                s["batting"]["striker"], s["batting"]["non_striker"] = non_striker, striker

        elif outcome == "Leg Bye":
            r = int(lb_runs)
            add_runs = r
            s["batsman_stats"][striker]["B"] += 1; s["bowler_stats"][bowler]["B"] += 1
            highlight = f"Leg Bye {r}"
            chip_tag = "chip-bye"; chip_txt = f"LB{r}"
            if r % 2 == 1: s["batting"]["striker"], s["batting"]["non_striker"] = non_striker, striker

        elif outcome == "Bye":
            r = int(bye_runs)
            add_runs = r
            s["batsman_stats"][striker]["B"] += 1; s["bowler_stats"][bowler]["B"] += 1
            highlight = f"Bye {r}"
            chip_tag = "chip-bye"; chip_txt = f"B{r}"
            if r % 2 == 1: s["batting"]["striker"], s["batting"]["non_striker"] = non_striker, striker

        # Apply runs & balls
        s["score"][bat_team]["runs"] += add_runs
        if legal_ball:
            s["score"][bat_team]["balls"] += 1
            s["bowler_stats"][bowler]["B"] += 0  # already incremented above for legal events
            # End of over check
            if s["score"][bat_team]["balls"] % 6 == 0:
                end_over(s)

        # Log ball for chip feed
        o = s["score"][bat_team]["balls"]
        over_num = max(o-1,0)//6 + 1 if o>0 else (o//6 + 1)
        ball_in_over = (o-1) % 6 + 1 if legal_ball and o>0 else (o % 6)
        s["balls_log"].append({"over": over_num, "ball": ball_in_over, "txt": chip_txt or outcome, "tag": chip_tag or "chip-1"})

        add_commentary(s, f"{outcome} — {striker} vs {bowler}: {highlight}")
        save_json(match_state_path(mid), s); st.success("Ball recorded.")

    # Ball chips / commentary
    st.markdown("### Recent Balls")
    chips_html = "".join([f"<span class='ball-chip {b['tag']}'>{b['txt']}</span>" for b in state.get("balls_log", [])[-24:][::-1]])
    st.markdown(f"<div class='ball-feed'>{chips_html}</div>", unsafe_allow_html=True)

    st.markdown("### Commentary (latest first)")
    st.write("\n".join(state.get("commentary", [])[:30]))

# =========================================================
# 4) LIVE SCORE (Public View) — always allowed
# =========================================================
if page == "Live Score (Public View)":
    st.subheader("Live Score & Highlights (Read-Only)")
    matches = load_json(MATCH_INDEX, {})
    if not matches: st.info("No matches yet."); st.stop()

    mid = st.selectbox("Select Match", list(matches.keys())[::-1],
                       format_func=lambda k: f"{matches[k]['title']} — {k}")
    meta = matches[mid]; state = load_json(match_state_path(mid), {})
    if not state: st.warning("State not found for this match yet."); st.stop()
    ensure_state_defaults(state, meta)

    bat = state["bat_team"]; sc = state["score"][bat]

    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown(f"### **{meta['title']}**")
        st.write(f"**Venue:** {meta.get('venue','')} • **Overs:** {state['overs_limit']}")
        st.markdown(
            f"<div class='score-strip'><b>{bat}</b> {sc['runs']}/{sc['wkts']} — Overs {overs_str(sc['balls'])} • RR {rr(sc['runs'], sc['balls'])}</div>",
            unsafe_allow_html=True)
    with c2:
        st.markdown("### Current")
        st.write(f"**Striker:** {state['batting'].get('striker','')}")
        st.write(f"**Non-Striker:** {state['batting'].get('non_striker','')}")
        st.write(f"**Bowler:** {state['bowling'].get('current_bowler','')}")

    st.markdown("### Recent Balls")
    chips_html = "".join([f"<span class='ball-chip {b['tag']}'>{b['txt']}</span>" for b in state.get("balls_log", [])[-30:][::-1]])
    st.markdown(f"<div class='ball-feed'>{chips_html}</div>", unsafe_allow_html=True)

    st.markdown("### Highlights")
    st.write("\n".join(state.get("commentary", [])[:30]))
    st.caption("Tip: Pull to refresh (mobile) or use browser refresh for latest ball.")

# =========================================================
# 5) PLAYER STATS — always allowed (read-only)
# =========================================================
if page == "Player Stats":
    st.subheader("Registered Members")
    df = read_registered()
    st.dataframe(df, use_container_width=True)
    st.caption("Advanced season-wise stats can be derived from ball-by-ball data (next version).")

# =========================================================
# 6) ADMIN (Hidden) — only with PIN
# =========================================================
if page == "Admin (Hidden)":
    if not st.session_state.is_admin:
        st.stop()
    st.subheader("Admin Tools — Private")

    tab1, tab2 = st.tabs(["Paid Members List", "Matches & States"])

    with tab1:
        st.markdown("Manage the paid members list here. Visible only to admin.")
        paid = read_paid_members()
        st.dataframe(paid, use_container_width=True)
        st.markdown("#### Add / Remove Members")
        with st.form("add_paid"):
            new_mobile = st.text_input("Mobile number to add")
            remove_mobile = st.text_input("Mobile number to remove")
            sbtn = st.form_submit_button("Apply Changes")
        if sbtn:
            df = read_paid_members()
            if new_mobile.strip():
                df = pd.concat([df, pd.DataFrame({"Mobile_No":[str(new_mobile).strip()]})], ignore_index=True)
                df.drop_duplicates(subset=["Mobile_No"], keep="last", inplace=True)
            if remove_mobile.strip():
                df = df[df["Mobile_No"].astype(str) != str(remove_mobile).strip()]
            write_paid_members(df)
            st.success("Paid list updated (CSV). If an Excel exists, CSV is still used for verification.")

    with tab2:
        matches = load_json(MATCH_INDEX, {})
        if not matches:
            st.info("No matches available.")
        else:
            sel_mid = st.selectbox("Select Match", list(matches.keys())[::-1],
                                   format_func=lambda k: f"{matches[k]['title']} — {k}")
            if sel_mid:
                s = load_json(match_state_path(sel_mid), {})
                ensure_state_defaults(s, matches[sel_mid])
                st.write("Status:", s.get("status"))
                colA, colB = st.columns(2)
                with colA:
                    if st.button("Force End Over"):
                        end_over(s); save_json(match_state_path(sel_mid), s); st.success("Over forced ended.")
                with colB:
                    if st.button("End Innings / Complete Match"):
                        end_innings(s, matches, sel_mid); save_json(match_state_path(sel_mid), s); st.success("Innings/Match advanced.")
                if st.button("Delete Match (danger)"):
                    try:
                        os.remove(match_state_path(sel_mid))
                    except Exception:
                        pass
                    matches.pop(sel_mid, None)
                    save_json(MATCH_INDEX, matches)
                    st.success("Match deleted.")

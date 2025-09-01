import streamlit as st
import pandas as pd
from PIL import Image, ImageDraw
import io, os
from datetime import datetime

# Load paid members list
paid_members = pd.read_excel("Members_Paid.xlsx")

# Load registered members file (create if not exists)
if os.path.exists("Registered_Members.xlsx"):
    registered = pd.read_excel("Registered_Members.xlsx")
else:
    registered = pd.DataFrame(columns=["Reg_No", "Name", "Mobile", "Branch", "Role"])
    registered.to_excel("Registered_Members.xlsx", index=False)

st.set_page_config(page_title="MPGB Cricket Club", layout="centered")

st.title("🏏 MPGB CRICKET CLUB – SAGAR")
st.subheader("Membership Registration Portal")

mobile = st.text_input("📱 Enter Mobile Number")

if st.button("Verify"):
    match = paid_members[paid_members['Mobile_No'].astype(str) == mobile]

    if not match.empty:
        st.success("✅ Membership Verified! Please complete your registration.")

        name = st.text_input("📝 Full Name")
        branch = st.text_input("🏦 Branch Code")
        role = st.selectbox("🎯 Playing Role", ["Batsman", "Bowler", "All-Rounder", "Wicketkeeper"])
        photo = st.file_uploader("📸 Upload Your Photo", type=["jpg", "png"])

        if st.button("Generate ID") and name and branch and photo:
            # Auto Registration Number
            next_no = len(registered) + 1
            reg_no = f"MPGBCC-{datetime.now().year}-{next_no:04d}"

            # Save to registered members
            new_data = pd.DataFrame([[reg_no, name, mobile, branch, role]],
                                    columns=registered.columns)
            registered = pd.concat([registered, new_data], ignore_index=True)
            registered.to_excel("Registered_Members.xlsx", index=False)

            # Create ID Card
            logo = Image.open("RRB_LOGO_new.png").resize((80, 100))
            user_img = Image.open(photo).resize((180, 180))

            card = Image.new("RGB", (600, 400), "white")
            card.paste(logo, (250, 10))
            card.paste(user_img, (30, 150))

            draw = ImageDraw.Draw(card)
            draw.text((200, 130), "MPGB CRICKET CLUB - SAGAR", fill="black")
            draw.text((250, 180), f"Name: {name}", fill="blue")
            draw.text((250, 210), f"Mobile: {mobile}", fill="black")
            draw.text((250, 240), f"Branch: {branch}", fill="black")
            draw.text((250, 270), f"Role: {role}", fill="black")
            draw.text((250, 300), f"Reg. No: {reg_no}", fill="red")

            st.image(card, caption="Your Membership ID Card")

            # Download button
            buf = io.BytesIO()
            card.save(buf, format="PNG")
            st.download_button(
                label="⬇️ Download ID Card",
                data=buf.getvalue(),
                file_name=f"{name}_ID.png",
                mime="image/png"
            )

    else:
        st.error("⚠️ Please deposit ₹500 membership fee to register.")

"""
Authentication UI for Streamlit frontend.
Renders login, doctor registration, and 4-step patient registration.
"""

import time
import streamlit as st
from utils.api_client import APIClient

# Initialize API Client
api_client = APIClient()

def render_api_configuration_sidebar():
    st.sidebar.markdown("### ⚙️ API Configuration")
    
    # Initialize api_keys if not present
    if "api_keys" not in st.session_state:
        st.session_state.api_keys = {}
        
    api_keys = st.session_state.api_keys
    
    groq_key = st.sidebar.text_input(
        "Groq API Key",
        type="password",
        value=api_keys.get("groq_key", ""),
        placeholder="gsk_..."
    )
    resend_key = st.sidebar.text_input(
        "Resend API Key",
        type="password",
        value=api_keys.get("resend_key", ""),
        placeholder="re_..."
    )
    twilio_sid = st.sidebar.text_input(
        "Twilio Account SID",
        type="password",
        value=api_keys.get("twilio_sid", ""),
        placeholder="AC..."
    )
    twilio_token = st.sidebar.text_input(
        "Twilio Auth Token",
        type="password",
        value=api_keys.get("twilio_token", ""),
        placeholder="auth_token"
    )
    twilio_phone = st.sidebar.text_input(
        "Twilio Phone Number",
        value=api_keys.get("twilio_phone", ""),
        placeholder="+1..."
    )
    doctor_email = st.sidebar.text_input(
        "Doctor Email",
        value=api_keys.get("doctor_email", ""),
        placeholder="doctor@example.com"
    )
    
    # Save to session state
    st.session_state.api_keys = {
        "groq_key": groq_key.strip(),
        "resend_key": resend_key.strip(),
        "twilio_sid": twilio_sid.strip(),
        "twilio_token": twilio_token.strip(),
        "twilio_phone": twilio_phone.strip(),
        "doctor_email": doctor_email.strip()
    }
    
    required = ["groq_key", "resend_key", "twilio_sid", "twilio_token", "twilio_phone", "doctor_email"]
    if all(st.session_state.api_keys.get(k) for k in required):
        st.sidebar.success("✅ API Keys configured")
    else:
        st.sidebar.warning("⚠️ API Keys missing")

def check_api_keys_configured() -> bool:
    if "api_keys" not in st.session_state or not st.session_state.api_keys:
        return False
    required = ["groq_key", "resend_key", "twilio_sid", "twilio_token", "twilio_phone", "doctor_email"]
    return all(st.session_state.api_keys.get(k) for k in required)

def render_auth_page():
    # Render API configuration sidebar on every page
    render_api_configuration_sidebar()
    
    if not check_api_keys_configured():
        st.warning("Please configure all API keys in the sidebar to continue")
        st.stop()

    # Initialize auth state if not present
    if "auth_page" not in st.session_state:
        st.session_state["auth_page"] = "login"
    if "reg_step" not in st.session_state:
        st.session_state["reg_step"] = 1
    if "reg_data" not in st.session_state:
        st.session_state["reg_data"] = {}

    page = st.session_state["auth_page"]

    # Render pages
    if page == "login":
        render_login()
    elif page == "register_doctor":
        render_doctor_registration()
    elif page == "register_patient":
        render_patient_registration()

def render_login():
    st.markdown("<div style='text-align: center; margin-top: 40px;'>", unsafe_allow_html=True)
    st.markdown("<h1 class='premium-glow-text' style='font-size: 2.85rem; margin-bottom: 8px;'>🏥 Healthcare Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-secondary); font-size: 1.1rem; font-weight: 500;'>Sign in to access your portal</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        with st.form("login_form", clear_on_submit=False):
            email = st.text_input("Email Address", placeholder="enter your email...")
            password = st.text_input("Password", type="password", placeholder="enter your password...")
            submit_button = st.form_submit_button("Sign In", use_container_width=True, type="primary")

            if submit_button:
                if not email or not password:
                    st.error("Please enter both email and password")
                else:
                    res = api_client.login(email, password)
                    if res and "error" in res:
                        st.error(f"❌ {res['error']}")
                    elif res and "session_token" in res:
                        # Store in session state
                        st.session_state["session_token"] = res["session_token"]
                        st.session_state["role"] = res["role"]
                        st.session_state["phone"] = res["phone"]
                        st.session_state["user_id"] = res["user_id"]
                        st.session_state["doctor_id"] = res.get("doctor_id", "") if res["role"] == "doctor" else ""
                        st.session_state["name"] = res["name"]
                        st.session_state["logged_in"] = True
                        
                        # Populate patient_profile default structure if patient
                        if res["role"] == "patient":
                            # Fetch patient details
                            details = api_client.get_patient_details(res["phone"])
                            if details:
                                # Convert medicines from DB format if list or JSON string
                                medicines = details.get("medicines") or []
                                if isinstance(medicines, str):
                                    import json
                                    try:
                                        medicines = json.loads(medicines)
                                    except Exception:
                                        medicines = []
                                profile_data = {
                                    "patient_name": details.get("name", ""),
                                    "age": details.get("age", 0),
                                    "gender": details.get("gender", ""),
                                    "height": details.get("height", 0.0),
                                    "weight": details.get("weight", 0.0),
                                    "phone_number": details.get("phone", ""),
                                    "email": details.get("email", ""),
                                    "medical_issue": details.get("medical_issue", ""),
                                    "doctor_name": details.get("doctor_name", ""),
                                    "doctor_email": details.get("doctor_email", ""),
                                    "doctor_phone": details.get("doctor_phone", ""),
                                    "emergency_contact": details.get("emergency_contact", ""),
                                    "current_medicines": medicines,
                                    "special_instructions": details.get("special_instructions", ""),
                                    "patient_id": details.get("patient_id", ""),
                                    "blood_group": details.get("blood_group", ""),
                                    "address": details.get("address", ""),
                                    "profile_status": details.get("profile_status", "Active"),
                                }
                                st.session_state["patient_profile"] = profile_data
                        
                        st.success("Successfully logged in!")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error("Login failed. Please verify your internet connection or server status.")

        st.markdown("<hr style='border: 1px solid #2d3748;'>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #94a3b8;'>Don't have an account?</p>", unsafe_allow_html=True)
        
        reg_col1, reg_col2 = st.columns(2)
        with reg_col1:
            if st.button("Register as Doctor", use_container_width=True):
                st.session_state["auth_page"] = "register_doctor"
                st.rerun()
        with reg_col2:
            if st.button("Register as Patient", use_container_width=True):
                st.session_state["auth_page"] = "register_patient"
                st.session_state["reg_step"] = 1
                st.session_state["reg_data"] = {}
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("⚙️ Reset API Gateway Configuration", use_container_width=True):
            for k in ["groq_api_key", "resend_api_key", "twilio_account_sid", "twilio_auth_token", "twilio_phone_number"]:
                st.session_state[k] = ""
            st.rerun()

def render_doctor_registration():
    st.markdown("<div style='text-align: center; margin-top: 30px;'>", unsafe_allow_html=True)
    st.markdown("<h2 class='premium-glow-text' style='font-size: 2.5rem; margin-bottom: 8px;'>🩺 Doctor Registration Portal</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-secondary); font-size: 1.1rem; font-weight: 500;'>Create your clinical practitioner profile</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([0.8, 1.5, 0.8])
    with col2:
        with st.form("doctor_reg_form"):
            name = st.text_input("Full Name", placeholder="e.g. Dr. Jane Smith")
            email = st.text_input(
                "Email Address", 
                help="To receive email alerts, enter the same email address that you have registered/verified on your Resend account."
            )
            phone = st.text_input(
                "Phone Number", 
                help="Enter the mobile number that you have verified in your Twilio account. This same number will be used for call forwarding alerts when you log in as a doctor."
            )
            specialization = st.text_input("Specialization", placeholder="e.g. Cardiology, General Medicine")
            clinic_name = st.text_input("Clinic Name")
            
            pwd_col1, pwd_col2 = st.columns(2)
            with pwd_col1:
                password = st.text_input("Password", type="password")
            with pwd_col2:
                confirm_password = st.text_input("Confirm Password", type="password")

            submit_button = st.form_submit_button("Complete Doctor Registration", use_container_width=True, type="primary")

            if submit_button:
                if not name or not email or not phone or not password:
                    st.error("Fields: Name, Email, Phone, and Password are required.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif password != confirm_password:
                    st.error("Passwords do not match.")
                else:
                    doc_data = {
                        "name": name,
                        "email": email,
                        "phone": phone,
                        "specialization": specialization,
                        "clinic_name": clinic_name,
                        "password": password
                    }
                    res = api_client.register_doctor_auth(doc_data)
                    if res and "error" in res:
                        st.error(f"❌ {res['error']}")
                    elif res and res.get("success"):
                        st.success(f"🎉 Registration successful! Assigned ID: {res['doctor_id']}")
                        time.sleep(1.5)
                        st.session_state["auth_page"] = "login"
                        st.rerun()
                    else:
                        st.error("Registration failed. Please try again.")

        if st.button("⬅️ Back to Sign In", use_container_width=True):
            st.session_state["auth_page"] = "login"
            st.rerun()

def render_patient_registration():
    st.markdown("<div style='text-align: center; margin-top: 20px;'>", unsafe_allow_html=True)
    st.markdown("<h2 class='premium-glow-text' style='font-size: 2.5rem; margin-bottom: 8px;'>👤 Patient Registration Portal</h2>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    step = st.session_state["reg_step"]

    # Step indicator tabs (Visual guide only, non-clickable)
    step_cols = st.columns(4)
    steps_titles = ["1. Account Details", "2. Personal Details", "3. Medical Details", "4. Select Doctor"]
    for i, title in enumerate(steps_titles):
        col_status = "⚠️" if i+1 > step else ("✅" if i+1 < step else "🔵")
        style = "font-weight: bold; color: #42a5f5;" if i+1 == step else "color: #94a3b8;"
        step_cols[i].markdown(f"<p style='text-align: center; {style}'>{col_status} {title}</p>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([0.5, 2.0, 0.5])
    with col2:
        # Step 1: Account Details
        if step == 1:
            st.subheader("Step 1: Account Credentials")
            with st.form("patient_step_1"):
                email = st.text_input("Email Address", value=st.session_state["reg_data"].get("email", ""))
                phone = st.text_input("Phone Number", value=st.session_state["reg_data"].get("phone", ""))
                password = st.text_input("Password", type="password")
                confirm_password = st.text_input("Confirm Password", type="password")
                
                next_btn = st.form_submit_button("Next Step ➡️", type="primary")
                if next_btn:
                    if not email or not phone or not password:
                        st.error("Email, Phone, and Password are required.")
                    elif len(password) < 8:
                        st.error("Password must be at least 8 characters long.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    else:
                        st.session_state["reg_data"]["email"] = email
                        st.session_state["reg_data"]["phone"] = phone
                        st.session_state["reg_data"]["password"] = password
                        st.session_state["reg_step"] = 2
                        st.rerun()

        # Step 2: Personal Details
        elif step == 2:
            st.subheader("Step 2: Personal Information")
            with st.form("patient_step_2"):
                p_data = st.session_state["reg_data"]
                name = st.text_input("Full Name", value=p_data.get("name", ""))
                
                det_col1, det_col2 = st.columns(2)
                with det_col1:
                    age = st.number_input("Age", min_value=0, max_value=120, value=int(p_data.get("age", 25)))
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(p_data.get("gender", "Male")))
                    blood_group = st.text_input("Blood Group (e.g. O+)", value=p_data.get("blood_group", ""))
                with det_col2:
                    height = st.number_input("Height (cm)", min_value=0.0, max_value=250.0, value=float(p_data.get("height", 170.0)))
                    weight = st.number_input("Weight (kg)", min_value=0.0, max_value=300.0, value=float(p_data.get("weight", 70.0)))
                    emergency_contact = st.text_input("Emergency Contact Number", value=p_data.get("emergency_contact", ""))

                address = st.text_area("Home Address", value=p_data.get("address", ""))
                
                nav_col1, nav_col2 = st.columns(2)
                with nav_col1:
                    prev_btn = st.form_submit_button("⬅️ Back")
                with nav_col2:
                    next_btn = st.form_submit_button("Next Step ➡️", type="primary")

                if prev_btn:
                    st.session_state["reg_step"] = 1
                    st.rerun()

                if next_btn:
                    if not name:
                        st.error("Name is required.")
                    else:
                        p_data["name"] = name
                        p_data["age"] = age
                        p_data["gender"] = gender
                        p_data["blood_group"] = blood_group
                        p_data["height"] = height
                        p_data["weight"] = weight
                        p_data["emergency_contact"] = emergency_contact
                        p_data["address"] = address
                        st.session_state["reg_data"] = p_data
                        st.session_state["reg_step"] = 3
                        st.rerun()

        # Step 3: Medical Details
        elif step == 3:
            st.subheader("Step 3: Medical Background")
            with st.form("patient_step_3"):
                p_data = st.session_state["reg_data"]
                medical_issue = st.text_area("Primary Medical Issue / History", value=p_data.get("medical_issue", ""))
                medicines_str = st.text_area("Current Medicines (one per line)", value="\n".join(p_data.get("medicines", [])))
                special_instructions = st.text_area("Special Instructions", value=p_data.get("special_instructions", ""))

                nav_col1, nav_col2 = st.columns(2)
                with nav_col1:
                    prev_btn = st.form_submit_button("⬅️ Back")
                with nav_col2:
                    next_btn = st.form_submit_button("Next Step ➡️", type="primary")

                if prev_btn:
                    st.session_state["reg_step"] = 2
                    st.rerun()

                if next_btn:
                    p_data["medical_issue"] = medical_issue
                    p_data["medicines"] = [line.strip() for line in medicines_str.split("\n") if line.strip()]
                    p_data["special_instructions"] = special_instructions
                    st.session_state["reg_data"] = p_data
                    st.session_state["reg_step"] = 4
                    st.rerun()

        # Step 4: Select Doctor
        elif step == 4:
            st.subheader("Step 4: Select a Doctor")
            
            p_data = st.session_state["reg_data"]
            selected_doctor_id = p_data.get("doctor_id")

            # Debounced Search Input simulation using st.text_input
            search_name = st.text_input("Search Doctor by Name...", key="doctor_search_bar")
            
            # Fetch doctors list matching query
            doctors_list = api_client.search_doctors(search_name)
            
            if not doctors_list:
                st.warning("No doctors found matching search criteria. Type a doctor name or register a doctor account first.")
            else:
                st.markdown("<p style='font-size: 0.9rem; color: #94a3b8;'>Select a doctor from the list below:</p>", unsafe_allow_html=True)
                
                # Render selectable doctor cards
                for doc in doctors_list:
                    doc_id = doc["doctor_id"]
                    doc_name = doc["name"]
                    spec = doc.get("specialization") or "General Medicine"
                    clinic = doc.get("clinic_name") or "Public Health Clinic"
                    
                    is_selected = (doc_id == selected_doctor_id)
                    border_color = "#1e88e5" if is_selected else "#2d3748"
                    bg_color = "#1a2333" if is_selected else "#0f131a"
                    
                    card_html = f"""
                    <div style="border: 2px solid {border_color}; background-color: {bg_color}; padding: 15px; border-radius: 8px; margin-bottom: 10px;">
                        <h4 style="margin: 0; color: #fafafa;">👨‍⚕️ {doc_name}</h4>
                        <p style="margin: 5px 0 0 0; color: #94a3b8; font-size: 0.9rem;">Specialization: {spec}</p>
                        <p style="margin: 2px 0 0 0; color: #94a3b8; font-size: 0.9rem;">Clinic: {clinic}</p>
                    </div>
                    """
                    st.markdown(card_html, unsafe_allow_html=True)
                    
                    # Selection button
                    if st.button(f"Select Dr. {doc_name}", key=f"select_doc_{doc_id}", use_container_width=True):
                        st.session_state["reg_data"]["doctor_id"] = doc_id
                        st.rerun()

            # Bottom buttons
            st.markdown("<br>", unsafe_allow_html=True)
            bot_col1, bot_col2, bot_col3 = st.columns([1, 1, 1])
            with bot_col1:
                if st.button("⬅️ Back", use_container_width=True):
                    st.session_state["reg_step"] = 3
                    st.rerun()
            with bot_col3:
                # Active button check
                is_ready = bool(selected_doctor_id)
                complete_btn = st.button("Complete Registration 🎉", disabled=not is_ready, use_container_width=True, type="primary")
                
                if complete_btn:
                    # Submit registration to API
                    res = api_client.register_patient_auth(st.session_state["reg_data"])
                    if res and "error" in res:
                        st.error(f"❌ {res['error']}")
                    elif res and res.get("success"):
                        st.success(f"🎉 Patient registration successful! Patient ID: {res['patient_id']}")
                        time.sleep(2.0)
                        # Reset reg state and redirect
                        st.session_state["auth_page"] = "login"
                        st.session_state["reg_step"] = 1
                        st.session_state["reg_data"] = {}
                        st.rerun()
                    else:
                        st.error("Failed to complete patient registration. Please verify details.")

        st.markdown("<br><hr style='border: 1px solid #2d3748;'>", unsafe_allow_html=True)
        if st.button("Cancel Registration", use_container_width=True):
            st.session_state["auth_page"] = "login"
            st.session_state["reg_step"] = 1
            st.session_state["reg_data"] = {}
            st.rerun()


def render_api_gateway_screen():
    st.markdown("<div style='text-align: center; margin-top: 40px;'>", unsafe_allow_html=True)
    st.markdown("<h1 class='premium-glow-text' style='font-size: 2.85rem; margin-bottom: 8px;'>🔐 API Gateway Configuration</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color: var(--text-secondary); font-size: 1.1rem; font-weight: 500;'>Configure your API credentials to enable all system features before proceeding to login.</p>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([0.8, 1.5, 0.8])
    with col2:
        # ── Credentials form ─────────────────────────────────────────────────
        with st.form("api_gateway_form"):
            st.markdown("##### 🤖 Groq")
            groq_key = st.text_input(
                "Groq API Key",
                type="password",
                value=st.session_state.get("groq_api_key", ""),
                placeholder="gsk_...",
            )
            st.caption("🔑 Obtain from [console.groq.com](https://console.groq.com). Powers the LLM risk classifier and RAG chat responses.")

            st.markdown("---")
            st.markdown("##### 📧 Resend")
            resend_key = st.text_input(
                "Resend API Key",
                type="password",
                value=st.session_state.get("resend_api_key", ""),
                placeholder="re_...",
            )
            st.caption("🔑 Obtain from [resend.com](https://resend.com). ⚠️ The email registered with this API key must be used as the Doctor's Email during Doctor Registration so alert emails are delivered correctly.")

            st.markdown("---")
            st.markdown("##### 📞 Twilio")
            twilio_sid = st.text_input(
                "Twilio Account SID",
                value=st.session_state.get("twilio_account_sid", ""),
                placeholder="AC...",
            )
            st.caption("Found in your Twilio console dashboard under Account Info.")
            twilio_token = st.text_input(
                "Twilio Auth Token",
                type="password",
                value=st.session_state.get("twilio_auth_token", ""),
                placeholder="Auth token from Twilio console",
            )
            st.caption("Found next to your Account SID in the Twilio console.")
            twilio_num = st.text_input(
                "Twilio Phone Number  (international format)",
                value=st.session_state.get("twilio_phone_number", ""),
                placeholder="+12025551234",
            )
            st.caption("Enter the virtual international number Twilio assigned to your account (e.g. +1…). ⚠️ When registering as a Doctor, use the same mobile number you verified in Twilio — calls will be forwarded to that verified number.")

            st.markdown("<br>", unsafe_allow_html=True)
            submit_button = st.form_submit_button(
                "Save & Proceed to Login →", use_container_width=True, type="primary"
            )

            if submit_button:
                if not groq_key or not resend_key or not twilio_sid or not twilio_token or not twilio_num:
                    st.error("All fields are required. Please fill in every credential before proceeding.")
                else:
                    st.session_state["groq_api_key"] = groq_key.strip()
                    st.session_state["resend_api_key"] = resend_key.strip()
                    st.session_state["twilio_account_sid"] = twilio_sid.strip()
                    st.session_state["twilio_auth_token"] = twilio_token.strip()
                    st.session_state["twilio_phone_number"] = twilio_num.strip()
                    st.success("✅ API credentials saved. Redirecting to login…")
                    time.sleep(0.5)
                    st.rerun()

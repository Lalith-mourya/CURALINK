import json
import urllib.request
import urllib.error
import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

from core.config import get_settings


def send_escalation_email(
    patient_name: str,
    patient_phone: str,
    doctor_name: str,
    doctor_email: str,
    risk_level: str,
    risky_text: str,
    message_history: list,
    doctor_phone: str,
    resend_key: str,
) -> bool:
    """
    Send an HTML escalation email to the doctor using Resend.
    Returns True on success, False on any failure.
    """
    if not resend_key:
        raise ValueError("resend_key")

    return _send_via_resend(
        api_key=resend_key,
        patient_name=patient_name,
        patient_phone=patient_phone,
        doctor_name=doctor_name,
        doctor_email=doctor_email,
        risk_level=risk_level,
        risky_text=risky_text,
        message_history=message_history,
        doctor_phone=doctor_phone,
    )


def _build_html_email_body(
    patient_name: str,
    patient_phone: str,
    doctor_name: str,
    risk_level: str,
    risky_text: str,
    message_history: list,
    doctor_phone: str,
    timestamp: str,
) -> str:
    """Build a professional, modern HTML email body for patient alerts."""
    import html
    escaped_patient_name = html.escape(patient_name)
    escaped_patient_phone = html.escape(patient_phone)
    escaped_doctor_name = html.escape(doctor_name)
    escaped_risk_level = html.escape(risk_level.upper())
    escaped_risky_text = html.escape(risky_text)
    escaped_doctor_phone = html.escape(doctor_phone)
    escaped_timestamp = html.escape(timestamp)

    last_messages = message_history[-5:] if message_history else []
    history_rows = ''
    if not last_messages:
        history_rows = (
            '<tr>'
            '<td colspan="2" style="padding: 12px 14px; color: #64748b; font-size: 14px; border-bottom: 1px solid #e2e8f0; text-align: center;">'
            'No prior messages.'
            '</td>'
            '</tr>'
        )
    else:
        for msg in last_messages:
            role = msg.get('role', 'unknown').lower()
            content = msg.get('content', msg.get('message', ''))
            escaped_content = html.escape(content)
            
            # Style the sender role badge
            if role in ('patient', 'user'):
                role_badge = '<span style="background-color: #e0f2fe; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase;">Patient</span>'
            elif role in ('assistant', 'bot', 'doctor agent'):
                role_badge = '<span style="background-color: #f1f5f9; color: #475569; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase;">Assistant</span>'
            else:
                role_badge = f'<span style="background-color: #f1f5f9; color: #475569; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase;">{html.escape(role.capitalize())}</span>'
                
            history_rows += (
                f'<tr style="border-bottom: 1px solid #e2e8f0;">'
                f'<td style="padding: 12px 14px; border-bottom: 1px solid #e2e8f0; vertical-align: top; white-space: nowrap;">{role_badge}</td>'
                f'<td style="padding: 12px 14px; border-bottom: 1px solid #e2e8f0; color: #334155; font-size: 14px; line-height: 1.5;">{escaped_content}</td>'
                f'</tr>'
            )

    html_template = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Urgent Patient Risk Alert</title>
</head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px 0; -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;">
    <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f4f6f9; width: 100%;">
        <tr>
            <td align="center" style="padding: 10px 0;">
                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="max-width: 600px; background-color: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                    <tr>
                        <td style="background-color: #e11d48; height: 6px; line-height: 6px; font-size: 6px;">&nbsp;</td>
                    </tr>
                    <tr>
                        <td style="padding: 24px 32px; text-align: left; background-color: #ffffff; border-bottom: 1px solid #f1f5f9;">
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                <tr>
                                    <td>
                                        <span style="display: inline-block; background-color: #ffe4e6; color: #e11d48; font-size: 12px; font-weight: 700; text-transform: uppercase; padding: 4px 10px; border-radius: 4px; letter-spacing: 0.5px; margin-bottom: 12px;">
                                            🚨 Emergency Escalation
                                        </span>
                                        <h1 style="margin: 0; color: #0f172a; font-size: 22px; font-weight: 700; line-height: 1.3;">
                                            Urgent Patient Risk Alert
                                        </h1>
                                        <p style="margin: 6px 0 0 0; color: #64748b; font-size: 14px;">
                                            Healthcare Assistant AI Portal
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 32px; background-color: #ffffff;">
                            <p style="margin: 0 0 20px 0; color: #334155; font-size: 16px; line-height: 1.5;">
                                Dear Dr. {escaped_doctor_name},
                            </p>
                            <p style="margin: 0 0 24px 0; color: #475569; font-size: 15px; line-height: 1.6;">
                                An automated risk assessment has flagged a patient message requiring your immediate attention. Details of the incident and conversation context are provided below.
                            </p>
                            
                            <h3 style="margin: 0 0 10px 0; color: #0f172a; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                                Patient Profile
                            </h3>
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="background-color: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; margin-bottom: 24px;">
                                <tr>
                                    <td style="padding: 14px 16px; border-bottom: 1px solid #e2e8f0;">
                                        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td width="35%" style="color: #64748b; font-size: 14px; font-weight: 500;">Patient Name:</td>
                                                <td style="color: #0f172a; font-size: 14px; font-weight: 600;">{escaped_patient_name}</td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 14px 16px; border-bottom: 1px solid #e2e8f0;">
                                        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td width="35%" style="color: #64748b; font-size: 14px; font-weight: 500;">Phone Number:</td>
                                                <td style="color: #0f172a; font-size: 14px; font-weight: 600;"><a href="tel:{escaped_patient_phone}" style="color: #0284c7; text-decoration: none;">{escaped_patient_phone}</a></td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 14px 16px;">
                                        <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                            <tr>
                                                <td width="35%" style="color: #64748b; font-size: 14px; font-weight: 500;">Risk Classification:</td>
                                                <td>
                                                    <span style="background-color: #fee2e2; color: #991b1b; font-size: 12px; font-weight: 700; text-transform: uppercase; padding: 2px 8px; border-radius: 4px; border: 1px solid #fecaca; display: inline-block;">
                                                        {escaped_risk_level}
                                                    </span>
                                                </td>
                                            </tr>
                                        </table>
                                    </td>
                                </tr>
                            </table>
                            
                            <h3 style="margin: 0 0 10px 0; color: #0f172a; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                                Flagged Message
                            </h3>
                            <div style="background-color: #fff5f5; border-left: 4px solid #f43f5e; border-radius: 0 6px 6px 0; padding: 16px; margin-bottom: 28px;">
                                <p style="margin: 0; color: #1e293b; font-size: 15px; font-style: italic; line-height: 1.6;">
                                    "{escaped_risky_text}"
                                </p>
                            </div>
                            
                            <h3 style="margin: 0 0 12px 0; color: #0f172a; font-size: 14px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">
                                Recent Chat Context
                            </h3>
                            <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%" style="border-collapse: collapse; width: 100%; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; margin-bottom: 24px;">
                                <thead>
                                    <tr style="background-color: #f1f5f9; border-bottom: 1px solid #e2e8f0;">
                                        <th width="25%" style="padding: 10px 14px; color: #475569; font-size: 11px; font-weight: 700; text-transform: uppercase; text-align: left; letter-spacing: 0.5px;">Sender</th>
                                        <th style="padding: 10px 14px; color: #475569; font-size: 11px; font-weight: 700; text-transform: uppercase; text-align: left; letter-spacing: 0.5px;">Message</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {history_rows}
                                </tbody>
                            </table>
                            
                            <div style="background-color: #eff6ff; border-left: 4px solid #3b82f6; border-radius: 0 6px 6px 0; padding: 16px; margin-bottom: 24px;">
                                <table role="presentation" border="0" cellpadding="0" cellspacing="0" width="100%">
                                    <tr>
                                        <td valign="top" style="padding-right: 12px; font-size: 18px; line-height: 1;">📞</td>
                                        <td>
                                            <p style="margin: 0; color: #1e3a8a; font-size: 13.5px; font-weight: 600; line-height: 1.5;">
                                                Automated Call Triggered
                                            </p>
                                            <p style="margin: 4px 0 0 0; color: #1e40af; font-size: 13px; line-height: 1.5;">
                                                An emergency text-to-speech call is currently being placed to your registered phone number: <strong>{escaped_doctor_phone}</strong>.
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </div>
                            
                            <p style="margin: 0; color: #94a3b8; font-size: 12px; text-align: right;">
                                Generated on: {escaped_timestamp}
                            </p>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 24px 32px; background-color: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center;">
                            <p style="margin: 0; color: #64748b; font-size: 12px; line-height: 1.5;">
                                This is an automated clinical notification from the Healthcare Assistant System.
                            </p>
                            <p style="margin: 6px 0 0 0; color: #94a3b8; font-size: 11px;">
                                Please do not reply directly to this email. For technical support, contact the system administrator.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""
    return html_template


def _send_via_resend(
    api_key: str,
    patient_name: str,
    patient_phone: str,
    doctor_name: str,
    doctor_email: str,
    risk_level: str,
    risky_text: str,
    message_history: list,
    doctor_phone: str,
) -> bool:
    """Send escalation email using Resend API."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    html_body = _build_html_email_body(
        patient_name=patient_name,
        patient_phone=patient_phone,
        doctor_name=doctor_name,
        risk_level=risk_level,
        risky_text=risky_text,
        message_history=message_history,
        doctor_phone=doctor_phone,
        timestamp=timestamp,
    )

    payload = {
        "from": "Healthcare Assistant <onboarding@resend.dev>",
        "to": [doctor_email],
        "subject": f"🚨 URGENT: Patient Risk Alert — {patient_name}",
        "html": html_body,
        "text": f"URGENT: Patient {patient_name} ({patient_phone}) has been flagged as {risk_level.upper()}. Message: {risky_text}"
    }

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "HealthcareApp/1.0"
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=15) as response:
            res_body = response.read().decode('utf-8')
            res_json = json.loads(res_body)
            print(f"[Email] Escalation email sent via Resend to {doctor_email}. Response ID: {res_json.get('id')}")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"[Email] Resend API HTTP Error {e.code}: {err_body}")
        return False
    except Exception as e:
        print(f"[Email] Failed to send email via Resend: {e}")
        return False


def _send_via_smtp(
    settings,
    patient_name: str,
    patient_phone: str,
    doctor_name: str,
    doctor_email: str,
    risk_level: str,
    risky_text: str,
    message_history: list,
    doctor_phone: str,
) -> bool:
    """Send escalation email using Gmail SMTP_SSL."""
    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    html_body = _build_html_email_body(
        patient_name=patient_name,
        patient_phone=patient_phone,
        doctor_name=doctor_name,
        risk_level=risk_level,
        risky_text=risky_text,
        message_history=message_history,
        doctor_phone=doctor_phone,
        timestamp=timestamp,
    )

    try:
        msg = EmailMessage()
        msg['Subject'] = f'🚨 URGENT: Patient Risk Alert — {patient_name}'
        msg['From'] = settings.SMTP_USER
        msg['To'] = doctor_email
        msg.set_content(
            f"URGENT: Patient {patient_name} ({patient_phone}) has been flagged "
            f"as {risk_level.upper()}. Message: {risky_text}"
        )
        msg.add_alternative(html_body, subtype='html')

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

        print(f"[Email] Escalation email sent to {doctor_email} via SMTP for patient {patient_name}.")
        return True

    except Exception as exc:
        print(f"[Email] Failed to send escalation email via SMTP: {exc}")
        return False

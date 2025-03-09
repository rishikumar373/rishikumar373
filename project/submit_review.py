import streamlit as st
import pandas as pd
import os
import uuid
from langchain_together import TogetherEmbeddings
from pinecone import Pinecone
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from textblob import TextBlob  # Sentiment analysis

# ✅ Page config - must be first Streamlit command
st.set_page_config(page_title="Submit Review", page_icon="📝")

# ✅ Set API Keys (for production, move to environment variables)
os.environ["TOGETHER_API_KEY"] = "4b35bf117de47f85e287445a758437a052494b4235ab5f7c28c9182e9ef4e06b"
PINECONE_API_KEY = 'pcsk_5Q9W8Y_TSK22TSphTofcH6KjpYv7dqDTVUQ83XLbfMFCfaT4uVv8Xy2a3bP8tEEpuitbkD'

# ✅ Initialize Pinecone client
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index("hotel")

# ✅ Initialize Together Embeddings
embeddings = TogetherEmbeddings(model="togethercomputer/m2-bert-80M-8k-retrieval")

# ✅ Path to Excel file
file_path = "D:\\reviews_data.xlsx"

# ✅ Load existing reviews data
if os.path.exists(file_path):
    df = pd.read_excel(file_path)
else:
    df = pd.DataFrame(columns=[
        "review_id", "display_id", "customer_id", "Rating", "Review",
        "review_date", "review_date_numeric", "stay_status"
    ])

# Ensure the 'display_id' column exists
if "display_id" not in df.columns:
    df["display_id"] = pd.Series([], dtype=int)

# ✅ Function to get next display_id (sequential 5-digit)
def get_next_display_id():
    if df.empty or df["display_id"].isnull().all():
        return 10001  # Start from 10001
    else:
        return int(df["display_id"].max()) + 1

# Function to send email notification
def send_email(subject, body, to_email):
    from_email = "rishikumar45628@gmail.com"
    from_password = "ajyt zwtd vtmz wamx"  # Use app-specific password if using Gmail
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject

    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Encrypt the connection
            server.login(from_email, from_password)
            server.sendmail(from_email, to_email, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")

# Function to analyze sentiment of the review
def analyze_sentiment(review_text):
    # Use TextBlob to analyze sentiment: Returns polarity (-1 = negative, 1 = positive)
    blob = TextBlob(review_text)
    polarity = blob.sentiment.polarity
    return polarity

# ✅ Streamlit App Title
st.title("📝 Submit Your Hotel Review")

# ✅ Review Submission Form
with st.form("review_form"):
    customer_id = st.text_input("Customer ID", placeholder="Enter your Customer ID")
    rating = st.slider("Rating (1-10)", 1, 10, 5)
    review_text = st.text_area("Your Review", placeholder="Write your review here...")
    review_date = st.date_input("Review Date", datetime.now())

    # ✅ New field - Customer stay status
    stay_status = st.radio(
        "Are you currently staying at the hotel or have you checked out?",
        ["Currently Staying", "Checked Out"]
    )

    submitted = st.form_submit_button("Submit Review")

# ✅ Handle form submission
if submitted:
    if not review_text.strip():
        st.error("⚠️ Review cannot be empty.")
    elif not customer_id.strip():
        st.error("⚠️ Customer ID cannot be empty.")
    else:
        # ✅ Generate review_id and display_id
        new_review_id = str(uuid.uuid4())
        new_display_id = get_next_display_id()

        # ✅ Convert review date to numeric format
        review_date_numeric = int(review_date.strftime("%Y%m%d"))

        # ✅ Create new review record
        new_review = {
            "review_id": new_review_id,
            "display_id": new_display_id,
            "customer_id": customer_id,
            "Rating": rating,
            "Review": review_text,
            "review_date": review_date.strftime("%Y-%m-%d"),
            "review_date_numeric": review_date_numeric,
            "stay_status": stay_status
        }

        # ✅ Save to DataFrame and Excel
        new_df = pd.DataFrame([new_review])
        df = pd.concat([df, new_df], ignore_index=True)
        df.to_excel(file_path, index=False)

        st.success(f"✅ Review Submitted Successfully (Review ID: {new_display_id})")

        # ✅ Embed review and upload to Pinecone
        with st.spinner("🔗 Uploading review to vector database..."):
            review_embedding = embeddings.embed_query(review_text)

            index.upsert(vectors=[(
                new_review_id,
                review_embedding,
                {
                    "review_id": new_review_id,
                    "display_id": new_display_id,
                    "customer_id": customer_id,
                    "Rating": rating,
                    "review_date": review_date_numeric,
                    "stay_status": stay_status
                }
            )])

        st.success("✅ Review successfully added to Pinecone Vector Database!")

        # ✅ Analyze sentiment of the review
        sentiment_polarity = analyze_sentiment(review_text)

        # ✅ If sentiment is negative (polarity < 0), send email
        if sentiment_polarity < 0:
            email_subject = "Negative Review Alert"
            email_body = (
                f"A negative review has been submitted by Customer ID: {customer_id}.\n\n"
                f"Rating: {rating}\n"
                f"Review: {review_text}\n\n"
                f"Stay Status: {stay_status}\n"
                f"Review Date: {review_date.strftime('%Y-%m-%d')}\n\n"
                f"Please review and take appropriate action."
            )
            manager_email = "rishikumard916@gmail.com"  # Replace with actual manager's email
            send_email(email_subject, email_body, manager_email)

# ✅ Footer
st.markdown("---")
st.markdown('<div style="text-align: center;">Built with ❤️ using Streamlit | 2025</div>', unsafe_allow_html=True)

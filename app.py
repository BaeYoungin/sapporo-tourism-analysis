import os
import io
import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
from docx import Document
from dotenv import load_dotenv
import tiktoken
from seed_documents import SEED_DOCUMENTS

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Document Analyzer",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
        .main-header {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(90deg, #6366f1, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.2rem;
        }
        .sub-header {
            color: #6b7280;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }
        .stat-card {
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 0.75rem;
            padding: 1rem 1.25rem;
            text-align: center;
        }
        .stat-value {
            font-size: 1.6rem;
            font-weight: 700;
            color: #4f46e5;
        }
        .stat-label {
            font-size: 0.8rem;
            color: #9ca3af;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .chat-message-user {
            background: #ede9fe;
            border-radius: 0.75rem;
            padding: 0.75rem 1rem;
            margin: 0.4rem 0;
        }
        .chat-message-assistant {
            background: #f3f4f6;
            border-radius: 0.75rem;
            padding: 0.75rem 1rem;
            margin: 0.4rem 0;
        }
        div[data-testid="stTabs"] button {
            font-weight: 600;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in {
    "doc_text": "",
    "doc_name": "",
    "chat_history": [],
    "summary": "",
    "insights": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_text(file) -> str:
    name = file.name.lower()
    if name.endswith(".pdf"):
        reader = PdfReader(io.BytesIO(file.read()))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if name.endswith(".docx"):
        doc = Document(io.BytesIO(file.read()))
        return "\n".join(p.text for p in doc.paragraphs)
    return file.read().decode("utf-8", errors="ignore")


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def truncate_to_tokens(text: str, max_tokens: int = 12_000, model: str = "gpt-4o-mini") -> str:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    return enc.decode(tokens[:max_tokens])


def get_client(api_key: str) -> OpenAI:
    return OpenAI(api_key=api_key)


def chat_completion(client: OpenAI, model: str, messages: list, stream: bool = True):
    return client.chat.completions.create(model=model, messages=messages, stream=stream)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 설정")

    api_key = st.text_input(
        "OpenAI API Key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        placeholder="sk-...",
        help="환경변수 OPENAI_API_KEY 또는 직접 입력",
    )

    model_choice = st.selectbox(
        "모델 선택",
        ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo"],
        index=0,
    )

    st.markdown("---")
    st.markdown("## 🎬 데모 문서")

    demo_labels = ["— 선택하세요 —"] + [d["label"] for d in SEED_DOCUMENTS]
    selected_demo = st.selectbox("샘플 문서 선택", demo_labels, label_visibility="collapsed")

    if selected_demo != "— 선택하세요 —":
        demo_doc = next(d for d in SEED_DOCUMENTS if d["label"] == selected_demo)
        if st.button("📂 데모 문서 불러오기", use_container_width=True, type="primary"):
            st.session_state.doc_text = demo_doc["text"]
            st.session_state.doc_name = demo_doc["name"]
            st.session_state.chat_history = []
            st.session_state.summary = ""
            st.session_state.insights = []
            st.rerun()

    st.markdown("---")
    st.markdown("## 📂 문서 업로드")

    uploaded_file = st.file_uploader(
        "PDF / DOCX / TXT",
        type=["pdf", "docx", "txt"],
        label_visibility="collapsed",
    )

    if uploaded_file:
        with st.spinner("문서를 읽는 중..."):
            text = extract_text(uploaded_file)
        if text.strip():
            st.session_state.doc_text = text
            st.session_state.doc_name = uploaded_file.name
            st.session_state.chat_history = []
            st.session_state.summary = ""
            st.session_state.insights = []
            st.success(f"✅ {uploaded_file.name}")
        else:
            st.error("텍스트를 추출할 수 없습니다.")

    if st.session_state.doc_text:
        token_count = count_tokens(st.session_state.doc_text, model_choice)
        word_count = len(st.session_state.doc_text.split())
        char_count = len(st.session_state.doc_text)

        st.markdown("---")
        st.markdown("### 📊 문서 통계")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{word_count:,}</div>'
                f'<div class="stat-label">단어</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="stat-card"><div class="stat-value">{token_count:,}</div>'
                f'<div class="stat-label">토큰</div></div>',
                unsafe_allow_html=True,
            )

        if st.button("🗑️ 문서 초기화", use_container_width=True):
            for k in ["doc_text", "doc_name", "chat_history", "summary", "insights"]:
                st.session_state[k] = [] if k in ("chat_history", "insights") else ""
            st.rerun()

# ── Main area ─────────────────────────────────────────────────────────────────
st.markdown('<p class="main-header">📄 AI Document Analyzer</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">문서를 업로드하고 AI로 요약 · Q&A · 핵심 인사이트를 추출하세요</p>',
    unsafe_allow_html=True,
)

if not st.session_state.doc_text:
    st.info("👈 왼쪽 사이드바에서 **데모 문서**를 선택하거나 PDF / DOCX / TXT 파일을 업로드하세요.")

    st.markdown("### 🎬 바로 체험해보기")
    cols = st.columns(len(SEED_DOCUMENTS))
    for col, doc in zip(cols, SEED_DOCUMENTS):
        with col:
            if st.button(doc["label"], use_container_width=True):
                st.session_state.doc_text = doc["text"]
                st.session_state.doc_name = doc["name"]
                st.session_state.chat_history = []
                st.session_state.summary = ""
                st.session_state.insights = []
                st.rerun()
    st.stop()

if not api_key:
    st.warning("🔑 OpenAI API Key를 사이드바에 입력하세요.")
    st.stop()

client = get_client(api_key)
doc_context = truncate_to_tokens(st.session_state.doc_text, max_tokens=12_000, model=model_choice)

tab_summary, tab_qa, tab_insights, tab_raw = st.tabs(
    ["📝 요약", "💬 Q&A 챗봇", "💡 핵심 인사이트", "📃 원문 보기"]
)

# ── Tab 1: Summary ────────────────────────────────────────────────────────────
with tab_summary:
    st.subheader("문서 요약")

    length_option = st.radio(
        "요약 길이",
        ["짧게 (3문장)", "보통 (한 단락)", "자세히 (불릿 포인트 포함)"],
        horizontal=True,
    )

    length_map = {
        "짧게 (3문장)": "3 sentences",
        "보통 (한 단락)": "one concise paragraph",
        "자세히 (불릿 포인트 포함)": "detailed bullet points covering main sections",
    }

    if st.button("🚀 요약 생성", use_container_width=True, type="primary"):
        st.session_state.summary = ""
        prompt = (
            f"다음 문서를 한국어로 {length_map[length_option]} 형식으로 요약해 주세요.\n\n"
            f"문서:\n{doc_context}"
        )
        messages = [
            {"role": "system", "content": "당신은 전문적인 문서 분석 AI 어시스턴트입니다."},
            {"role": "user", "content": prompt},
        ]
        with st.spinner("요약 중..."):
            placeholder = st.empty()
            full_response = ""
            for chunk in chat_completion(client, model_choice, messages, stream=True):
                delta = chunk.choices[0].delta.content or ""
                full_response += delta
                placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
            st.session_state.summary = full_response

    elif st.session_state.summary:
        st.markdown(st.session_state.summary)

# ── Tab 2: Q&A Chatbot ────────────────────────────────────────────────────────
with tab_qa:
    st.subheader("문서 기반 Q&A")

    chat_container = st.container(height=420)
    with chat_container:
        if not st.session_state.chat_history:
            st.markdown(
                "<div style='color:#9ca3af;text-align:center;padding:2rem;'>"
                "문서에 대해 무엇이든 질문하세요 💬</div>",
                unsafe_allow_html=True,
            )
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="chat-message-user">🧑 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f'<div class="chat-message-assistant">🤖 {msg["content"]}</div>',
                    unsafe_allow_html=True,
                )

    with st.form("chat_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])
        with col_input:
            user_input = st.text_input(
                "질문 입력",
                placeholder="예: 이 문서의 주요 결론은 무엇인가요?",
                label_visibility="collapsed",
            )
        with col_btn:
            submitted = st.form_submit_button("전송", use_container_width=True, type="primary")

    if submitted and user_input.strip():
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        system_msg = (
            "당신은 주어진 문서를 기반으로 질문에 답하는 AI입니다. "
            "반드시 문서 내용에 근거하여 한국어로 답변하세요. "
            "문서에 없는 내용은 '문서에서 확인할 수 없습니다'라고 명시하세요."
        )
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"문서 내용:\n{doc_context}"},
            {"role": "assistant", "content": "문서를 분석했습니다. 질문하세요."},
            *[
                m for m in st.session_state.chat_history
                if not (m["role"] == "user" and m["content"] == user_input)
            ],
            {"role": "user", "content": user_input},
        ]

        with st.spinner("답변 생성 중..."):
            full_response = ""
            for chunk in chat_completion(client, model_choice, messages, stream=True):
                full_response += chunk.choices[0].delta.content or ""

        st.session_state.chat_history.append({"role": "assistant", "content": full_response})
        st.rerun()

    if st.session_state.chat_history and st.button("대화 초기화", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

# ── Tab 3: Key Insights ───────────────────────────────────────────────────────
with tab_insights:
    st.subheader("핵심 인사이트 추출")

    insight_type = st.selectbox(
        "분석 유형",
        [
            "핵심 주제 및 논점",
            "행동 항목 / 할 일 목록",
            "주요 수치 및 데이터",
            "결론 및 권고사항",
            "위험 요소 및 문제점",
        ],
    )

    if st.button("💡 인사이트 추출", use_container_width=True, type="primary"):
        prompt = (
            f"다음 문서에서 '{insight_type}'를 한국어로 추출해 주세요. "
            "각 항목을 번호 목록으로 명확하게 작성하세요.\n\n"
            f"문서:\n{doc_context}"
        )
        messages = [
            {"role": "system", "content": "당신은 전문적인 문서 분석 AI입니다."},
            {"role": "user", "content": prompt},
        ]
        with st.spinner("분석 중..."):
            placeholder = st.empty()
            full_response = ""
            for chunk in chat_completion(client, model_choice, messages, stream=True):
                full_response += chunk.choices[0].delta.content or ""
                placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
            st.session_state.insights = full_response

    elif st.session_state.insights:
        st.markdown(st.session_state.insights)

# ── Tab 4: Raw text ───────────────────────────────────────────────────────────
with tab_raw:
    st.subheader(f"원문: {st.session_state.doc_name}")
    st.text_area(
        "원문 내용",
        value=st.session_state.doc_text,
        height=500,
        label_visibility="collapsed",
    )
    st.download_button(
        "⬇️ 텍스트 다운로드",
        data=st.session_state.doc_text,
        file_name=st.session_state.doc_name.rsplit(".", 1)[0] + "_extracted.txt",
        mime="text/plain",
        use_container_width=True,
    )

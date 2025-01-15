import streamlit as st
import pyperclip
from openai import OpenAI

def copy_to_clipboard(text):
    pyperclip.copy(text)

# Show title and description.
st.title("💬 Chatbot")
st.write(
    "This is a simple chatbot that uses OpenAI's GPT-4 model to generate responses. "
    "Chat with the bot and provide feedback using the thumbs up/down buttons. "
    "You can learn how to build this app step by step by [following our tutorial](https://docs.streamlit.io/develop/tutorials/llms/build-conversational-apps)."
)

# Create an OpenAI client using the API key from secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Create a session state variable to store the chat messages. This ensures that the
# messages persist across reruns.
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display the existing chat messages via `st.chat_message`.
for i, message in enumerate(st.session_state.messages):
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            feedback = message.get("feedback", None)
            col1, col2, col3, col4 = st.columns([0.1, 0.1, 0.1, 0.7])
            with col1:
                if st.button("📋", key=f"copy_{i}"):
                    copy_to_clipboard(message["content"])
            with col2:
                thumbs_up_style = {"backgroundColor": "#28a745", "color": "white"} if feedback == "thumbs_up" else {}
                if st.button("👍", key=f"thumbs_up_{i}", type="primary" if feedback == "thumbs_up" else "secondary"):
                    st.session_state.messages[i]["feedback"] = "thumbs_up"
                    st.rerun()
            with col3:
                thumbs_down_style = {"backgroundColor": "#dc3545", "color": "white"} if feedback == "thumbs_down" else {}
                if st.button("👎", key=f"thumbs_down_{i}", type="primary" if feedback == "thumbs_down" else "secondary"):
                    st.session_state.messages[i]["feedback"] = "thumbs_down"
                    st.rerun()

# Create a chat input field to allow the user to enter a message. This will display
# automatically at the bottom of the page.
if prompt := st.chat_input("What is your query human?"):

    # Store and display the current prompt.
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate a response using the OpenAI API.
    stream = client.chat.completions.create(
            model="gpt-4",
        messages=[
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages
        ],
        stream=True,
    )

    # Stream the response to the chat using `st.write_stream`, then store it in 
    # session state.
    with st.chat_message("assistant"):
        response = st.write_stream(stream)
    st.session_state.messages.append({"role": "assistant", "content": response})

    # Add thumbs up and thumbs down buttons after the assistant's response.
    feedback = st.session_state.messages[-1].get("feedback", None)
    col1, col2, col3, col4 = st.columns([0.1, 0.1, 0.1, 0.7])
    with col1:
        if st.button("📋", key=f"copy_{len(st.session_state.messages)-1}"):
            copy_to_clipboard(st.session_state.messages[-1]["content"])
    with col2:
        thumbs_up_style = {"backgroundColor": "#28a745", "color": "white"} if feedback == "thumbs_up" else {}
        if st.button("👍", key=f"thumbs_up_{len(st.session_state.messages)}", type="primary" if feedback == "thumbs_up" else "secondary"):
            st.session_state.messages[-1]["feedback"] = "thumbs_up"
            st.rerun()
    with col3:
        thumbs_down_style = {"backgroundColor": "#dc3545", "color": "white"} if feedback == "thumbs_down" else {}
        if st.button("👎", key=f"thumbs_down_{len(st.session_state.messages)}", type="primary" if feedback == "thumbs_down" else "secondary"):
            st.session_state.messages[-1]["feedback"] = "thumbs_down"
            st.rerun()

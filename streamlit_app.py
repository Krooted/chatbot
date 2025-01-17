import streamlit as st
import pyperclip
import openai
import pandas as pd
from vanna.remote import VannaDefault
import psycopg2
from psycopg2.extras import RealDictCursor

def copy_to_clipboard(text):
    pyperclip.copy(text)

# Initialize Vanna AI with OpenAI
# email = st.secrets["VANNA_AI_EMAIL"]
api_key = st.secrets["VANNA_AI_API_KEY"]
model = "thrive" 
vn = VannaDefault(api_key=api_key, model=model)

# PostgreSQL Connection
conn = psycopg2.connect(
    host=st.secrets["postgres"]["host"],
    port=st.secrets["postgres"]["port"],
    database=st.secrets["postgres"]["database"],
    user=st.secrets["postgres"]["user"],
    password=st.secrets["postgres"]["password"],
    cursor_factory=RealDictCursor
)

vn.connect_to_postgres(
    host=st.secrets["postgres"]["host"],
    dbname=st.secrets["postgres"]["database"],
    user=st.secrets["postgres"]["user"],
    password=st.secrets["postgres"]["password"], 
    port=st.secrets["postgres"]["port"]
)

# Train Vanna on database schema
@st.cache_resource
def train_vanna():
    # Get database schema
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            table_schema,
            table_name,
            column_name,
            data_type,
            is_nullable
        FROM 
            information_schema.columns
        WHERE 
            table_schema = 'public'
        ORDER BY 
            table_schema, table_name, ordinal_position;
    """)
    schema_info = cursor.fetchall()
    
    # Format schema for training
    ddl = []
    current_table = None
    for row in schema_info:
        if current_table != row['table_name']:
            if current_table is not None:
                ddl.append(');')
            current_table = row['table_name']
            ddl.append(f"\nCREATE TABLE {row['table_name']} (")
        else:
            ddl.append(',')
        
        nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
        ddl.append(f"\n    {row['column_name']} {row['data_type']} {nullable}")
    
    if ddl:  # Close the last table
        ddl.append(');')
    
    # Sample SQL query for training
    sample_sql_query = "select count(*) from public.patients; select * from medical_records;;"

    vn.train('\n'.join(ddl), sample_sql_query)
    cursor.close()

# Train Vanna before user interaction
train_vanna()

df_test = vn.run_sql("SELECT 1")
print(df_test)

# Create an OpenAI client for general chat
# openai.api_key = st.secrets["OPENAI_API_KEY"]

# Show title and description
st.title("💬 Database-Aware Chatbot")
st.write(
    "This chatbot uses OpenAI's GPT-4 model and Vanna AI to understand and query the database. "
    "Ask questions about the data and get SQL-powered responses. "
    "Provide feedback using the thumbs up/down buttons."
)

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

    # OpenAI Stuff
    # client = openai

    # Generate a response using the OpenAI API.
    # response = client.chat.completion.create(
    #     model="gpt-4",
    #     messages=[
    #         {"role": m["role"], "content": m["content"]}
    #         for m in st.session_state.messages
    #     ],
    #     stream=True,
    # )

       # Ask Vanna the most recent question from the most recent chat entry
    most_recent_question = st.session_state.messages[-1]["content"]

    # allow_llm_to_see_data=True allows Vanna to see the database data... This occured when I asked it which patients were female
    most_recent_sql = vn.generate_sql(most_recent_question, allow_llm_to_see_data=True)
    print(most_recent_sql)
    vanna_response = vn.run_sql(most_recent_sql) 
    print(vanna_response)
    # this doesnt appear to return anything different then the response itself
    vanna_follow_up_questions = vn.generate_followup_questions(most_recent_question, most_recent_sql, vanna_response)
    print(vanna_follow_up_questions)
    # vanna_plotly_code = vn.generate_plotly_code(vanna_response)
    # vanna_plotly_figure = vn.get_plotly_figure(vanna_plotly_code)
    
    # Append the response and follow-up questions to the chat
    st.session_state.messages.append({"role": "assistant", "content": vanna_response})
    st.session_state.messages.append({"role": "assistant", "content": vanna_follow_up_questions})
     # Display Vanna's response
    # with st.chat_message("assistant"):
    #     st.markdown(vanna_response)
    # Display Vanna's response in a grid-like format
    with st.chat_message("assistant"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### Response")
            df = pd.DataFrame(vanna_response)
            st.dataframe(df)
        with col2:
            st.markdown("### Follow-up Questions")
            for question in vanna_follow_up_questions:
                st.markdown(f"- {question}")

    # Stream the response to the chat using `st.write_stream`, then store it in 
    # session state.
    # with st.chat_message("assistant"):
    #     st.markdown(response.choices[0].message["content"])
    # st.session_state.messages.append({"role": "assistant", "content": response.choices[0].message["content"]})

    # Add thumbs up and thumbs down buttons after the assistant's response.
    # col1, col2 = st.columns([1, 1])
    # with col1:
    #     if st.button("👍", key=f"thumbs_up_{len(st.session_state.messages)}"):
    #         st.session_state.messages[-1]["feedback"] = "thumbs_up"
    # with col2:
    #     if st.button("👎", key=f"thumbs_down_{len(st.session_state.messages)}"):
    #         st.session_state.messages[-1]["feedback"] = "thumbs_down"

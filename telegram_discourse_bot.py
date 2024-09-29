import json
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackQueryHandler
from telegram.helpers import escape_markdown
import requests
import aiohttp
from langchain.chains import RetrievalQA
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
from uuid import uuid4

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Dictionary to store user messages and answers using unique IDs
user_queries = {}

# Initialize the embedding model (to use with the retriever)
embedding_model = HuggingFaceEmbeddings(model_name='sentence-transformers/all-MiniLM-L6-v2')
# Load the FAISS vector store
vector_store = FAISS.load_local("faiss_index", embeddings=embedding_model)
#print('This works')
# Create a retriever from the vector store
retriever = vector_store.as_retriever(embedding_model=embedding_model, search_kwargs={"k": 5})
#print(retriever)

# Telegram bot token
TELEGRAM_TOKEN = "7828063944:AAHJLgBukbYVIBM-z76avyVpNKoteXBfPDY"

# Google Gemini Flash API configuration
GEMINI_FLASH_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"
GEMINI_API_KEY = "AIzaSyCKab4R5XTuarzUfIHOVckm3jc2sGkdBpY"

# Function to call Google Gemini Flash API
async def generate_answer_with_gemini_flash(prompt):
    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        'contents': [{'parts': [{'text': prompt}]}]
    }
    url = f"{GEMINI_FLASH_API_URL}?key={GEMINI_API_KEY}"
    
    # Debugging: print the payload and URL
    print(f"Sending request to URL: {url}")
    print(f"Payload: {json.dumps(payload)}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=json.dumps(payload), timeout=60) as response:
                print(f"Response Status Code: {response.status}")
                response_text = await response.text()
                print(f"Full Response Text: {response_text}")
                
                if response.status == 200:
                    result = await response.json()
                    try:
                        candidates = result.get('candidates', [])
                        if candidates and isinstance(candidates, list):
                            content = candidates[0].get('content', {})
                            parts = content.get('parts', [])
                            if parts and isinstance(parts, list):
                                return parts[0].get('text', 'No text found in the response.')
                            else:
                                return 'No valid parts found in the response.'
                        else:
                            return 'No valid candidates found in the response.'
                    except Exception as e:
                        print(f"Error while parsing response: {e}")
                        return 'Error parsing the response from the API.'
                else:
                    return f"Failed to connect to the Gemini Flash API: {response.status} - {response_text}"
        except Exception as e:
            print(f"HTTP request error: {e}")
            return 'Failed to make the API request due to a network issue.'


# Function to retrieve documents and generate an answer
async def get_answer(question):
    # Retrieve relevant documents
    docs = retriever.get_relevant_documents(question)
    
    # Combine the documents into a single context, prioritizing those containing keywords
    context = "\n".join([doc.page_content for doc in docs if 'India' in doc.page_content or 'RTI' in doc.page_content])
    
    # If no directly relevant documents, use the first retrieved documents as fallback
    if not context:
        context = "\n".join([doc.page_content for doc in docs[:2]])

    # Limit context length to a certain number of characters
    max_context_length = 2000
    if len(context) > max_context_length:
        context = context[:max_context_length] + "\n[Content truncated]..."

    # Modify the prompt to use the context for answering
    prompt = (
        f"Please provide an answer to the question using the information in the documents below:\n\n"
        f"Documents:\n{context}\n\nQuestion: {question}\nAnswer:"
    )

    # Generate the answer using the Gemini Flash API
    return await generate_answer_with_gemini_flash(prompt)


# Handler function for incoming messages

async def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    logger.info(f"Received message from user: {user_message}")
    
    # Classify the question using the LLM
    category = await classify_question_with_llm(user_message)
    logger.info(f"Classified category: {category}")

    # Generate an answer using the RAG framework and Gemini Flash API
    answer = await get_answer(user_message)
    logger.info(f"Generated answer: {answer}")

    # Generate a unique ID for this interaction
    message_id = str(uuid4())
    # Store the user message, answer, and category in the dictionary
    user_queries[message_id] = {'question': user_message, 'answer': answer, 'category': category}

    try:
        # Escape the answer for MarkdownV2
        escaped_answer = escape_markdown(answer, version=2)
        
        # Check if the answer exceeds Telegram's character limit
        max_message_length = 4096
        if len(escaped_answer) > max_message_length:
            # Split the answer into chunks
            for i in range(0, len(escaped_answer), max_message_length):
                await update.message.reply_text(f"**Answer (part):** {escaped_answer[i:i + max_message_length]}", parse_mode='MarkdownV2')
        else:
            await update.message.reply_text(f"**Answer:** {escaped_answer}", parse_mode='MarkdownV2')

        # Ask for user feedback with the assigned category
        keyboard = [
            [InlineKeyboardButton("Yes", callback_data=f'feedback_yes|{message_id}'),
             InlineKeyboardButton("No", callback_data=f'feedback_no|{message_id}')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(f'This question is categorized under "{category}". Are you satisfied with the response?', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error sending message to Telegram: {e}")


async def handle_feedback(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()  # Acknowledge the callback query

    # Extract the callback data
    callback_data = query.data

    if callback_data.startswith('feedback_no'):
        # Get the message_id from the callback data
        message_id = callback_data.split('|', 1)[1]
        # Retrieve the user's question and answer from the dictionary
        user_message = user_queries[message_id]['question']
        answer = user_queries[message_id]['answer']

        # Ask the user if they want to post the question to the community
        keyboard = [
            [InlineKeyboardButton("Yes", callback_data=f'post_to_community|{message_id}'),
             InlineKeyboardButton("No", callback_data=f'ask_feedback|{message_id}')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text('Would you like to post this question to the community for further discussion?', reply_markup=reply_markup)

    elif callback_data.startswith('post_to_community'):
        # Get the message_id from the callback data
        message_id = callback_data.split('|', 1)[1]
        # Retrieve the user's question and answer from the dictionary
        user_message = user_queries[message_id]['question']
        answer = user_queries[message_id]['answer']

        # Post the question and initial answer to Discourse
        #await post_to_discourse(user_message, answer, category_name)
        await post_to_discourse(user_message, answer)

        # Notify the user
        await query.edit_message_text("Your question has been posted to the community forum.")

    elif callback_data.startswith('ask_feedback'):
        # Ask the user for feedback on why they were not satisfied
        await query.edit_message_text("Please provide feedback on why you weren't satisfied with the response.")


# Start command handler
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text('Hello! Send me a question, and I will provide an answer based on our documents.')

async def post_to_discourse(question, answer):
    # Discourse API details
    discourse_url = "https://dtest.wi0lono.com/posts.json"
    discourse_api_key = "0208f4bb232be3793ff52c7aacab79e08cb4a9c2ccf0e53fb667cb1858d982b1"
    discourse_username = "dontcompute"
    headers = {
        'Api-Key': discourse_api_key,
        'Api-Username': discourse_username,
        'Content-Type': 'application/json'
    }
    
    # Mapping of bot categories to Discourse category IDs
    category_id_mapping = {
        "General": 4,
        "Cyber laws": 17,
        "Transgender rights": 19,
        "Violence against women": 20,
        "Property law": 21,
        "Right to information": 22,
        "Welfare schemes": 23,
        "Engagement with police": 24
    }

    # Get the category ID based on the classification
    #category_id = category_id_mapping.get(category_name, 4)  # Default to "General" (ID: 4) if category not found

    # Prepare the data to post
    data = {
        'title': f"User Question: {question[:50]}...",  # Use the first 50 characters of the question as the title
        'raw': f"**Question:** {question}\n\n**Initial Answer:** {answer}",
        'category': 2 #TODO
    }
    
    # Post to Discourse
    async with aiohttp.ClientSession() as session:
        async with session.post(discourse_url, headers=headers, json=data) as response:
            if response.status == 200:
                #logger.info(f"Successfully posted to Discourse under category ID {category_id}.")
                logger.info(f"Succesfully posted to discourse!")
            else:
                logger.error(f"Failed to post to Discourse: {response.status} - {await response.text()}")


async def classify_question_with_llm(question):
    # Define the categories and associated keywords for preliminary filtering
    category_keywords = {
        "Labour law": ["labour", "employment", "workplace", "worker", "salary", "employee", "employer", "boss", "payment", "work", "factory",],
        "Cyber laws": ["cyber", "internet", "digital", "online", "hacking", "photo", "password", "harassment", "computer", "phone", "data"],
        "Transgender rights": ["transgender", "lgbt", "gender identity", "queer", "trans"],
        "Violence against women": ["violence", "abuse", "domestic", "harassment", "women", "beaten", "hit", "wife", "husband", "in-law", "sexual harassment", "rape"],
        "Property law": ["property", "land", "ownership", "inheritance"],
        "Right to information": ["RTI", "right to information", "disclosure", "information"],
        "Welfare schemes": ["welfare", "scheme", "benefits", "government aid"],
        "Engagement with police": ["police", "law enforcement", "crime", "report", "arrest"]
    }

    # Preliminary keyword-based check
    for category, keywords in category_keywords.items():
        if any(keyword.lower() in question.lower() for keyword in keywords):
            logger.info(f"Keyword-based classification: {category}")
            return category

    # If no keyword match found, use LLM for classification
    prompt = (
        f"Classify the following question into one of these categories: {', '.join(category_keywords.keys())}.\n"
        f"Here are some examples to help you classify:\n"
        f"1. 'What are the rights of workers in a factory?' -> Labour law\n"
        f"2. 'How to file an RTI application?' -> Right to information\n"
        f"3. 'What are the legal protections for transgender individuals?' -> Transgender rights\n"
        f"4. 'What steps can I take if my property is being encroached?' -> Property law\n"
        f"5. 'How to report online harassment?' -> Cyber laws\n"
        f"6. 'What are the welfare schemes for senior citizens?' -> Welfare schemes\n"
        f"7. 'How can I engage with the police for a complaint?' -> Engagement with police\n"
        f"8. 'What laws protect women against domestic violence?' -> Violence against women\n\n"
        f"Now, classify the following question:\n"
        f"Question: {question}\n"
        f"Category:"
    )

    headers = {
        'Content-Type': 'application/json'
    }
    payload = {
        'contents': [{'parts': [{'text': prompt}]}]
    }
    url = f"{GEMINI_FLASH_API_URL}?key={GEMINI_API_KEY}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, data=json.dumps(payload), timeout=60) as response:
                if response.status == 200:
                    result = await response.json()
                    try:
                        candidates = result.get('candidates', [])
                        if candidates and isinstance(candidates, list):
                            content = candidates[0].get('content', {})
                            parts = content.get('parts', [])
                            if parts and isinstance(parts, list):
                                # Extract the category from the LLM's response
                                category = parts[0].get('text', '').strip()
                                logger.info(f"LLM classification output: {category}")
                                # Ensure the response is one of the predefined categories
                                if category in category_keywords:
                                    return category
                                else:
                                    logger.warning(f"Unexpected category returned: {category}")
                    except Exception as e:
                        logger.error(f"Error while parsing response: {e}")
        except Exception as e:
            logger.error(f"HTTP request error during classification: {e}")
    
    # Fallback to "General" if classification fails
    return "General"

def main():
    # Create the Application
    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add command handler to start the bot
    application.add_handler(CommandHandler('start', start))

    # Add message handler for text messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Add callback query handler for feedback
    application.add_handler(CallbackQueryHandler(handle_feedback))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
#logger.info(f"Response JSON: {result}")
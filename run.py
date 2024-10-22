from flask import Flask, request, render_template
from flask_cors import CORS
from generate_embedding import Chatbot, OllamaChatbot
from io import BytesIO
from PyPDF2 import PdfReader
import requests


app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET", "POST"])
def index():
    return render_template("index.html")


@app.route("/process_pdf", methods=['POST'])
def process_pdf():
    print("Processing pdf")
    file = request.data
    pdf = PdfReader(BytesIO(file))
    chatbot = Chatbot()  # Default to OpenAI
    if request.args.get('provider') == 'ollama':
        chatbot = OllamaChatbot()
    paper_text = chatbot.parse_paper(pdf)
    global df
    df = chatbot.paper_df(paper_text)
    df = chatbot.calculate_embeddings(df)
    print("Done processing pdf")
    return {'answer': ''}


@app.route("/download_pdf", methods=['POST'])
def download_pdf():
    chatbot = Chatbot()  # Default to OpenAI
    if request.args.get('provider') == 'ollama':
        chatbot = OllamaChatbot()
    url = request.json['url']
    r = requests.get(str(url))
    print(r.headers)
    pdf = PdfReader(BytesIO(r.content))
    paper_text = chatbot.parse_paper(pdf)
    global df
    df = chatbot.paper_df(paper_text)
    df = chatbot.calculate_embeddings(df)
    print("Done processing pdf")
    return {'key': ''}


@app.route("/reply", methods=['POST'])
def reply():
    chatbot = Chatbot()  # Default to OpenAI
    if request.args.get('provider') == 'ollama':
        chatbot = OllamaChatbot()
    query = request.json['query']
    query = str(query)
    prompt = chatbot.create_prompt(df, query)
    response = chatbot.response(df, prompt)
    print(response)
    return response, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)

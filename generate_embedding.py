import pandas as pd
from openai.embeddings_utils import get_embedding, cosine_similarity
import openai
import os
import logging as logger
from flask_cors import CORS
import os
openai.api_key = os.getenv('OPENAI_API_KEY')

class Chatbot():

    def parse_paper(self, pdf):
        logger.info("Parsing paper")
        number_of_pages = len(pdf.pages)
        logger.info(f"Total number of pages: {number_of_pages}")
        paper_text = []
        for i in range(number_of_pages):
            page = pdf.pages[i]
            page_text = []

            def visitor_body(text, cm, tm, fontDict, fontSize):
                x = tm[4]
                y = tm[5]
                # ignore header/footer
                if (y > 50 and y < 720) and (len(text.strip()) > 1):
                    page_text.append({
                        'fontsize': fontSize,
                        'text': text.strip().replace('\x03', ''),
                        'x': x,
                        'y': y
                    })

            _ = page.extract_text(visitor_text=visitor_body)

            blob_font_size = None
            blob_text = ''
            processed_text = []

            for t in page_text:
                if t['fontsize'] == blob_font_size:
                    blob_text += f" {t['text']}"
                    if len(blob_text) >= 2000:
                        processed_text.append({
                            'fontsize': blob_font_size,
                            'text': blob_text,
                            'page': i
                        })
                        blob_font_size = None
                        blob_text = ''
                else:
                    if blob_font_size is not None and len(blob_text) >= 1:
                        processed_text.append({
                            'fontsize': blob_font_size,
                            'text': blob_text,
                            'page': i
                        })
                    blob_font_size = t['fontsize']
                    blob_text = t['text']
                paper_text += processed_text
        logger.info("Done parsing paper")
        return paper_text

    def paper_df(self, pdf):
        logger.info('Creating dataframe')
        filtered_pdf= []
        for row in pdf:
            if len(row['text']) < 30:
                continue
            if len(row['text']) > 8000:
                row['text'] = row['text'][:8000]
            filtered_pdf.append(row)
        df = pd.DataFrame(filtered_pdf)
        # remove elements with identical df[text] and df[page] values
        df = df.drop_duplicates(subset=['text', 'page'], keep='first')
        df['length'] = df['text'].apply(lambda x: len(x))
        logger.info('Done creating df')
        return df

    def calculate_embeddings(self, df):
        logger.info('Calculating embeddings')
        embedding_model = "text-embedding-ada-002"
        embeddings = df.text.apply([lambda x: get_embedding(x, engine=embedding_model)])
        df["embeddings"] = embeddings
        logger.info('Done calculating embeddings')
        return df

    def search_embeddings(self, df, query, n=2, pprint=True):
        query_embedding = get_embedding(
            query,
            engine="text-embedding-ada-002"
        )
        df["similarity"] = df.embeddings.apply(lambda x: cosine_similarity(x, query_embedding))

        results = df.sort_values("similarity", ascending=False, ignore_index=True)
        results = results.head(n)
        global sources
        sources = []
        for i in range(n):
            # append the page number and the text as a dict to the sources list
            sources.append({'Page '+str(results.iloc[i]['page']): results.iloc[i]['text'][:150]+'...'})
        print(sources)
        return results.head(n)

    def create_prompt(self, df, user_input, strategy=None):
        result = self.search_embeddings(df, user_input)
        if strategy == "paper":
            prompt = """You are a large language model whose expertise is reading and summarizing scientific papers.
            You are given a query and a series of text embeddings from a paper in order of their cosine similarity to the query.
            You must take the given embeddings and return a very detailed summary of the paper that answers the query.
                Given the question: """+ user_input + """
                
                and the following embeddings as data: 
                
                1.""" + str(result.iloc[0]['text']) + """
                2.""" + str(result.iloc[1]['text']) + """
    
                Return a concise and accurate answer:"""
        elif strategy == "handbook":
            prompt = """You are a large language model whose expertise is reading and summarizing financial handbook.
            You are given a query and a series of text embeddings from a handbook in order of their cosine similarity to the query.
            You must take the given embeddings and return a very detailed answer in Chinese of the handbook that answers the query.
            If not necessary, your answer please use the original text as much as possible.
            You should also ensure that your response is written in clear and concise Chinese, using appropriate grammar and vocabulary.  
            Additionally, your response should focus on answering the specific query provided..
                Given the question: """+ user_input + """
                and the following embeddings as data: 
                
                1.""" + str(result.iloc[0]['text']) + """
                2.""" + str(result.iloc[1]['text']) + """
    
                Return a concise and accurate answer:"""
        elif strategy == "contract":
            prompt = """As a large language model specializing in reading and summarizing, your task is to read a query and a sequence of text inputs sorted by their cosine similarity to the query.
             Your goal is to provide a Chinese answer to the query using the given padding. If possible, please use the original text of your answer. 
             Please ensure that your response adheres to the terms of the agreement. Your response should focus on addressing the specific query provided, 
             providing relevant information and details based on the input texts' content. You should also strive for clarity and conciseness in your response, 
             summarizing key points while maintaining accuracy and relevance. Please note that you should prioritize understanding the context and meaning 
             behind both the query and input texts before generating a response.
                Given the question: """+ user_input + """
                and the following embeddings as data: 
                
                1.""" + str(result.iloc[0]['text']) + """
                2.""" + str(result.iloc[1]['text']) + """
    
                Return a concise and accurate answer:"""
        else:
            prompt = """As a language model specialized in reading and summarizing documents, your task is to provide a concise answer in Chinese based on a given query and a series of text embeddings from the document. 
            The embeddings are provided in order of their cosine similarity to the query. Your response should use as much original text as possible. 
            Your answer should be highly concise and accurate, providing relevant information that directly answers the query. 
            You should also ensure that your response is written in clear and concise Chinese, using appropriate grammar and vocabulary. 
            Please note that you must use the provided text embeddings to generate your response, which means you will need to understand how they relate to the original document. 
            Additionally, your response should focus on answering the specific query provided..
                Given the question: """+ user_input + """
                
                and the following embeddings as data: 
                
                1.""" + str(result.iloc[0]['text']) + """
                2.""" + str(result.iloc[1]['text']) + """
    
                Return a concise and accurate answer:"""
        logger.info('Done creating prompt')
        return prompt

    def response(self, df, prompt):
        logger.info('Sending request to GPT-3')
        prompt = self.create_prompt(df, prompt)
        r = openai.Completion.create(model="gpt-3.5-turbo", prompt=prompt, temperature=0.4, max_tokens=1500)
        answer = r.choices[0]['text']
        logger.info('Done sending request to GPT-3')
        response = {'answer': answer, 'sources': sources}
        return response


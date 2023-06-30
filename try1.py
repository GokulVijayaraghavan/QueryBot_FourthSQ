import os
import sys
import openai
import datetime
import threading
import logging
import pandas as pd
import gradio as gr
from pymongo import MongoClient
from openai.embeddings_utils import cosine_similarity

logging.basicConfig(filename='sys.log', filemode='w', format='%(asctime)s-%(name)s-%(levelname)s:%(message)s',level=logging.INFO)

username = os.getenv("MONGO_USERNAME")
pwd = os.getenv("ACCESS_KEY")
cluster = os.getenv("CLUSTER")
openai.api_key=os.getenv("OPENAI_KEY")

client = MongoClient("mongodb+srv://"+username+":"+pwd+"@"+cluster+"/?retryWrites=true&w=majority")
logging.info(client.test_database)
db = client["katefarms_db"]
collection = db["chatlog_collection"]

class chatgpt:
      
    def __init__(self,filename):
        self.chatlog = []
        self.db = []
        self.pre_prompt = "You're a friendly chatbot to answer questions related to Kate farms products alone. If an irrelevant or confusing or tricky question is asked say 'I can't answer'. Answer the question as truthfully as possible using the provided context, and if the answer is not contained within the context text below, say 'I don't know' Here is an example -> \n user : Who is batman? assistant: Sorry this is an out of context question not related to Kate farms. I can't answer. \n Context about Kate farms and its products -> \n"
        self.knowledge_df= pd.read_pickle(filename)
        self.previews = []
        self.content_index = []
        self.links = []
        self.titles = []
        self.system = []
        self.content = []

    def save_user(self,msg):
        data = {"user":msg, "timestamp":str(datetime.datetime.now())}
        self.chatlog.append({"role":"user","content":msg})
        self.db.append(data)
        collection.insert_one(data)
        logging.info("Saved user message")
        
    def save_assistant(self,msg,temperature, content_index, token_usage):
        data = {"assistant":msg, "temperature":temperature, "contents":content_index, "token_usage":token_usage,"timestamp":str(datetime.datetime.now())}
        self.db.append(data)
        self.chatlog.append({"role":"assistant","content":msg})
        collection.insert_one(data)
        logging.info("Saved server response")

    def view_chatlog(self):
        return self.chatlog
    
    def view_db(self):
        return self.db
    
    def update_system(self):
        self.system = [{"role": "system", "content": self.pre_prompt+self.content}]
    
    def return_chatlog(self,n=2):
        i = -1-(n*2)
        return self.system+self.chatlog[i:]
    
    def return_user_question(self):
        try:
            if self.chatlog[-1]['role'] == 'user':
                return self.chatlog[-1]['content']
            else:
                return self.chatlog[-2]['content']
        except:
            logging.warning("Return user question Error")
    
    def search_docs(self,n=3):
        y = openai.Embedding.create(model="text-embedding-ada-002",input=self.return_user_question())["data"][0]["embedding"]
        self.knowledge_df['similarities'] = self.knowledge_df.ada_embeddings.apply(lambda x: cosine_similarity(x, y))
        res_df = self.knowledge_df.sort_values('similarities', ascending=False).head(n)
        tl = 3000
        chosen_sections = []
        token_length = 0
        i=0
        if self.content_index == list(res_df.index)[:n]:
            logging.info("Content not replaced")
            return 
        else: 
            logging.info("Content replaced")
            for idx,row in res_df.iterrows():
                token_length += row['tokens']
                if token_length < tl:
                    i+=1
                    chosen_sections.append('\nContent '+str(i)+'-> '+str(row['content']))
                else:
                    break
            
            self.content = " ".join(chosen_sections)
            self.content_index = list(res_df.index)[:n]
            self.previews = list(res_df['preview'])[:n]
            self.links = list(res_df['link'])[:n]
            self.titles = list(res_df['title'])[:n]
            self.update_system()
    
    def chat_completion(self,temp=0.5):
        self.search_docs()
        logging.info("Sending request to the server")
        response =  openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            temperature = temp,
            messages = self.return_chatlog(3)
        )
        logging.info("Saving server response")
        resp = response.choices[0].message.content
        t2 = threading.Thread(target=self.save_assistant,args=(resp,temp,self.content_index,response.usage.total_tokens,))
        t2.start()                  
        msg = resp+'\n\nLearn More: \n'
        for i in range(0,3):
            temp_str = self.titles[i]+': '+self.links[i]+'\n'+self.previews[i]+'\n\n'
            msg = msg+temp_str
        return msg
    
chat=chatgpt("knowledge.pkl")

def user(chatlog, new_msg,chat = chat):
    if bool(new_msg.strip()):
        logging.info("Saving user question")
        chatlog = chatlog + [(new_msg, None)]
        t1 = threading.Thread(target=chat.save_user, args=(new_msg,))
        t1.start()
    else:
        logging.info("Empty message from user")
        pass
    return chatlog, ""

def server(chatlog,access_key,temperature,chat=chat):
    if access_key == pwd:
        if temperature == None:
            temperature = 0.5 
        response = chat.chat_completion(temperature)
    else:
        response = "Invalid Access Key!"
    chatlog[-1][1] = response
    return chatlog

with gr.Blocks(theme=gr.themes.Base(),title="GPT-3 Search Bot") as block:
    gr.Markdown("# Dynamic Chat Bot")   
    gr.Markdown("### Disclaimer: ")
    gr.Markdown("Please do not share any personal information with this chatbot. Any requests made to the chatbot are saved for the purpose of improving its functionality and enhancing its accuracy. Please note that this chatbot is still in its development stage and may not provide 100% accurate information. Use the information provided by the chatbot at your own discretion. We are constantly working to improve the chatbot's capabilities and appreciate your feedback to help us do so.")
    with gr.Row():
        with gr.Column():
            access_key = gr.Textbox(type='password',label="Access Key",show_label=True)
            temperature = gr.Slider(label="Temperature", minimum=0, maximum=1, step=0.1, value=0.1)
            gr.Markdown('### Important Information: ')
            gr.Markdown('Please note that the information provided by this chatbot is generated by AI and may contain errors or inaccuracies. It is not intended to be a substitute for professional medical advice, diagnosis, or treatment. Please consult with a healthcare provider before making any dietary or supplement changes. For customer support, please contact our customer service team - [Contact Us](https://help.katefarms.com/s/contactus)')
            
        with gr.Column():
            chatbot = gr.Chatbot()
            message = gr.Textbox(label="Type your question here")
            state = gr.State()
            message.submit(user, [chatbot, message], [chatbot, message]).then(server,[chatbot,access_key,temperature], chatbot)
            submit = gr.Button("Send",variant='primary')
            submit.click(user, [chatbot, message], [chatbot,message]).then(server, [chatbot,access_key,temperature], chatbot)
            gr.Examples([["Tell me about the nutrition shake."], ["Can I exchange a Kate farms product"],
               ["What is the size of nutrition shake pack?"],
               ["What is the minimum required age for consuming nutrition shake?"], 
               ["What are all the available flavors of nutrition shake?"], 
               ["Tell me about the sugar content in nutrition shake?"], 
               ["Is there a coffee flavor in standard 1.0?"], 
               ["Give me the recipe for Sun Butter Smoothie."],
               ["Is the nutrition shake organic and gluten-free?"], 
               ["Tell me about the ingredients in nutrition shakes"], 
               ["Can I return the product if I'm not satisfied?"],
               ["Allergen info for the nutrition shake"], 
               ["Can I tube feed nutrition shake?"], 
               ["How to return an order?"], ["Why should I purchase kate farms products"],
               ["What products can I tube feed?"],
               ["Tell me about the new Dell XPS notebook"],["Who is Batman?"]], message)
        
if __name__ == "__main__":
    block.launch(debug=False)
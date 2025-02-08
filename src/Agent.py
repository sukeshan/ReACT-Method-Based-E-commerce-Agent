
import re
import os

from dotenv import load_dotenv
from openai import OpenAI

from src.prompt import react_style_prompt
from src.template import all_tools
from src.Tool import Tools

load_dotenv(".env")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")

class ecommerceAgent:
    def __init__(self, system=""):
        self.system = system
        self.messages = []
        if self.system:
            self.messages.append({"role": "system", "content": system})

    def __call__(self, message):
        self.messages.append({"role": "user", "content": message})
        result = self.execute()
        self.messages.append({"role": "assistant", "content": result})
        return result

    def execute(self):
        client = OpenAI()

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=self.messages,
            temperature=0.01
        )
        
        return response.choices[0].message.content

class productSearch:
    """"""
    def __init__(self):
        self.bot = ecommerceAgent(react_style_prompt)    
        self.tools = Tools()

    def search(self, question):
        
        next_prompt = question
        result = self.bot(next_prompt)

        print("Model Response ",result)

        tools_params = [i.replace("**Action:**",'').strip() for i in result.split('\n') if i != "" and "**Action:**" in i ][0]

        necessary_tools  = {k : True  if k in result else  False  for k,v in all_tools.items()}

        # Regex to extract key-value pairs
        matches = re.findall(r'(\w+):("[^"]+"|\d+)', tools_params.split("|")[1])

        # Convert matches to a dictionary
        params = {k: v.strip('"') if v.startswith('"') else int(v) for k, v in matches}
        try:
            products = self.tools.main(params, necessary_tools)
        except Exception as error :
            print("error while fetching the product from ther platforms :", error)
            products = { "walmart" : {"products" :[]}, "amazon" :{"products" :[]}}

        next_prompt = " Summarize the below Observation in 300 characters in structured format:\n Observation: {}".format(products)
        
        observation = self.bot(next_prompt)

        return products, necessary_tools, observation

    

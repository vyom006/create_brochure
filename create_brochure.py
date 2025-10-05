'''
A] Business Problem:
Create a brochure from a website's link. The website will have different products listed there. 
The brochure should have all the products listed in the website and it should target potential 
investors, clients, and recruits.

B] Strategy
We need to scape the website. Then get all the product info from it. Then provide all these product 
info as input token to the open ai api and ask it to summarize. Then create pdf document out of it.
'''

import requests
import os
from dotenv import load_dotenv
from openai import OpenAI
from bs4 import BeautifulSoup
import json
import gradio as gr


# A) get the api key and validate its format
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
if api_key and api_key.startswith('sk-proj-') and len(api_key)>10:
    print("API key looks good so far")
else:
    print("There might be a problem with your API key? Please visit the troubleshooting notebook!")
 
# B) declare the LLM model to use
MODEL = 'gpt-4o-mini'

# C) initialize open ai object 
openai_object = OpenAI()

# D) Scraping the website
# The "Website" class here represents the website and also in the constructor, the "requests"
# library is used to scrape its contents and extract title, body, name, links 
# title, body, and links are stored as attributes in the website object
# get_contents() function returns the title and text (tags like img, script, style etc are removed) 
# of the website

# headers = { "User-Agent": "curl/7.79.1" }
class Website:
    def __init__(self, url):
        self.url = url
        # scrape using 'requests' library
        response = requests.get(self.url)#, headers=headers)
        self.body = response.content
        
        # use BeautifulSoup for easy parsing
        soup = BeautifulSoup(self.body, 'html.parser')
        self.title = soup.title if soup.title else 'No title found'
        # remove unnecessary html tags like script, img etc
        if soup.body:
            for irrelevant in soup.body(['sript', 'img', 'style', 'input']):
                irrelevant.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
        else:
            self.text = ""

        # very important part now: get all the hyperlinks
        links = [link.get('href') for link in soup.find_all('a')]
        self.links = [link for link in links if link]
    
    def get_contents(self):
        return f"Webpage title: {self.title} \n Webpage contents: \n{self.text}\n"
# -- end of class Website --


# E) Now, use Open AI's LLM to 
# send all the links to openai's llm and ask to prepare a summary
# but not all the links will be relevant, hence we'll have to somehow figure out the relevant links
# for us, it'll be very difficult to figure out what links will be relevant to generate a sales brochure 
# hence, we'll send all these links to openai LLM and ask it to create a list of important links
# we'll of course provide an one-shot or multi-shot example for the llm to identify important links

# now, let's create a system prompt (can be thought of a step to fine-tune or instruct the LLM) 
# one-shot prompt below
# Imp Note: Mentioning that the response needs to be in JSON is extremeley important, rather mandatory here. Else LLM will not send the response in JSON format.
#           mentioning JSON as the response type is mandatory here even if you put the response_format as JSON while calling the chat.completions.create() api
def set_system_prompt_for_the_llm_to_extract_links():
    # print("Activating system prompt instructions for the LLM.")
    link_system_prompt = "You are given a list links found on a webpage. \
    You are able to decide which of these links will be most relevant to include in a brochure about the company. \
    Such as a link to company page, about page, careers/jobs page, products/services/solutions page, use cases pages. \n"
    link_system_prompt += "You should respond in a JSON format as shown in the example:"
    link_system_prompt += """
    { 
        "links": [
            { "type": "About Page", "url": "https://full.url/goes/here/about },
            { "type": "careers page", "url": "https://another.full.url/careers" }
        ]
    }
    """
    return link_system_prompt


# the function below will create the user prompt
def create_all_links_and_corresponding_user_prompt(website):
    # print("--- Inside create_all_links_and_corresponding_user_prompt() function  --- ")
    user_prompt = f"Below is the list of links found on the website: {website.url}."
    user_prompt += "Please decide which of these links are relevant links to include in the brochure of the company. \
                    Respond with full https URL and do not include Terms of Service, Privacy, email links etc. "
    user_prompt += "Links (some might be relative links): "
    user_prompt += "\n".join(website.links)
    return user_prompt


# now, let's call the openai llm, pass it all the links, and ask for only the relevant links
def get_relevant_links_for_brochure_from_llm(url):
    # print("inside get_relevant_links_for_brochure_from_llm. calling Website(url)")
    website = Website(url)
    # print("after Website(url) call ")
    
    # activate the system prompt or instructions for the llm
    system_prompt_for_llm = set_system_prompt_for_the_llm_to_extract_links()

    user_prompt_ready_to_be_sent_to_llm = create_all_links_and_corresponding_user_prompt(website)
    # print("Calling chat completions api with full system and user prompt to get back all the relevant links")
    # print("calling openai now ...")
    openai_response = openai_object.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role":"system", "content": system_prompt_for_llm},
                        {"role": "user", "content": user_prompt_ready_to_be_sent_to_llm}
                    ],
                    response_format= {"type": "json_object"}
                )
    result = openai_response.choices[0].message.content
    # print("result received from openai. ")
    return result


# Now, let's go step-by-step
# step-1: call get_relevant_links_for_brochure_from_llm() by passing the website 
# this will call openai llm to provide us with all the relevant links
# step-2: let's use those relevant links, and again pass those to openai and ask to summarize

def set_system_prompt_for_the_llm_to_summarize():
    system_prompt_for_each_link = "You are an assistant that analyzes the contents of a Webpage \
        and provides a short summary, ignoring text that might be navigation related. \
        Create a segment title aligning with the contents of this webpage. \
        Respond in JSON. \
        "
    return system_prompt_for_each_link

def user_prompt_for_llm_to_summarize_each_webpage(link, page_content):
    user_prompt_for_each_link = f"Here is the content of the page: {page_content}"
    user_prompt_for_each_link += "Create a summary of this page's contents. Create a justifying Section title. Respond in JSON"

    return user_prompt_for_each_link


# now, loop through all the links of the website and call the summarizer
def call_summarizer_on_each_link(website_link=None):
    # website_link = "https://www.databricks.com/" # "https://www.learn-and-grow.tech" 
    # print(f"\nBrochure to be generated for website: {website_link} \n")
    all_links_for_brochure = get_relevant_links_for_brochure_from_llm(website_link)
    all_links_for_brochure = json.loads(all_links_for_brochure)
    # print("all_links_for_brochure: ")
    # print(all_links_for_brochure)
    all_page_summaries = ""
    system_prompt_for_the_llm_to_summarize = set_system_prompt_for_the_llm_to_summarize()
    for link in all_links_for_brochure["links"]:
        current_link = link['url']        
        content_of_each_link = Website(current_link).get_contents() # format: f"Webpage title: {self.title} \n Webpage contents: \n{self.text}\n"
        
        user_prompt_for_each_link = user_prompt_for_llm_to_summarize_each_webpage(link['url'], content_of_each_link)
        openai_response = openai_object.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role":"system", "content": system_prompt_for_the_llm_to_summarize},
                        {"role": "user", "content": user_prompt_for_each_link}
                    ],
                    response_format= {"type": "json_object"}
                )
        result = openai_response.choices[0].message.content         
        all_page_summaries += result   
        # print("Generated all page summaries")     
        return all_page_summaries

# below function uses openai as the final summarizer
def create_brochure(all_page_summaries):   
    print(" \n---> Generating Brochure in Markdown --->\n") 
    system_prompt_for_brochure_creation = "You are a great assistant who creates a brochure for a company given the summarized contents \
        of all the important pages of the website. User will provide you all the contents of a particular website and you need to create \
        a brochure for that website. Identify the type of the website given. For example, it may be a product & services company;  \
        in that case, in the brochure you mention those products & services provided by the company -- of course in a summarized format. You \
        may also include reference links to specific products or services there.\
        Another example is, may be the website is a educational website or a blog. In that case, create the brochure in a way that  \
        summarizes all the blog posts created by the author. For each blog post, either use the same title or a meaningful similar title and  \
        summarize the contents of that blog. If possible, mention the link for that specific blog. Also some blogs have info about the author(s). \
        If the authors' info is available, summarize that too in the brochure. Use proper title/heading/section header for this. \
        Now, one important aspect during the brochure creation is the target audience. The target audience includes:  \
        a potential investor, and existing investor, an existing customer, a potential customer,  a potential job  candidate, a board member,  \
        , and the CEO of the company. Hence create the brochure accordingly. Mention all important info in the brochure so that every   \
        target audience has something there to get interested Respond in Markdown format only. Use proper Markdown headings, lists, and formatting.\
        "
    user_prompt_for_brochure_creation = f"Here is the summary of all the contents of all the important pages of a website: {all_page_summaries}"
    user_prompt_for_brochure_creation += "Create a brochure for this website."
    openai_response = openai_object.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {"role":"system", "content": system_prompt_for_brochure_creation},
                        {"role": "user", "content": user_prompt_for_brochure_creation}
                    ],                    
                )
    markdown_brochure = openai_response.choices[0].message.content  
    print("\n!! Markdown received from LLM. Now Generating Brochure in .MD ...\n")
    
    # Write to a new .md file
    with open("brochure.md", "w", encoding="utf-8") as f:
        f.write(markdown_brochure)

    print("'brochure.md' generated!!")
    # Return the generated markdown so callers (and UI) can use it directly
    return markdown_brochure

def main(website_link=None):
    all_contents_of_the_website = call_summarizer_on_each_link(website_link)
    brochure = create_brochure(all_contents_of_the_website)
    # Return the brochure markdown so Gradio can display it
    return brochure

# Use a multiline textbox for input and a Markdown output so the brochure renders correctly
# Build a Blocks UI so we can show a loading spinner while the LLM runs
with gr.Blocks(title="Website to Brochure Generator") as demo:
    gr.Markdown("# Website to Brochure Generator")
    with gr.Row():
        input_url = gr.Textbox(lines=2, placeholder="Enter a website URL here, e.g. https://www.example.com")
        submit_btn = gr.Button("Generate Brochure")

    # Markdown output component (Gradio's queue will show a processing state/spinner)
    with gr.Row():
        with gr.Column():
            brochure_md = gr.Markdown(label="Brochure:")

    # Wire the button to call main and put result into the Markdown component
    submit_btn.click(fn=main, inputs=[input_url], outputs=[brochure_md])

demo.queue().launch()



# main(website_link = "https://openai.com/")
# main(website_link = "https://www.databricks.com/")

# main(website_link = "https://www.learn-and-grow.tech")
# main(website_link = "https://www.nvidia.com/en-us/")
# main(website_link = "https://www.coursera.org/")
# main(website_link = "https://www.snowflake.com/")
# main(website_link = "https://www.zomato.com/")
# main(website_link = "https://www.tesla.com/")
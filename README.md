# Company Brochure Generator
- This project generates a company's brochure from its website. 
- You don't have to link multiple links, just give the root website link
- For example: https://www.microsoft.com
- And it'll generate a brochure for you.

## Setup and run
1. clone the repo / download the code
2. create a virtual env: python -m venv venv
3. activate virtual env: source venv/bin/activate
4. install packages: pip install -r requirements.txt 
5. create .env file and give your Open AI API key as: OPENAI_API_KEY=sk...
6. execute: python create_brochure.py
    - Gradio will create a UI server (generally at: port 7860 on your local machine)
    - open: http://127.0.0.1:7860/ and give your website link and click 'Generate Brochure'
    - You'll see the brochure contents on the UI
    - And the markdown format of the brochure in your project's root folder 
    - multiple runs of the program will over-write the same file named 'brochure.md'

## LLM Models used
- Open AI

## UI
- gradio 

## TODO: Optimization
- Don't summarize each page separately. 
- Rather, combine the contents of each page and send that to LLM to summarize
- Improvement by this: N number of LLM calls to be reduced, whereas N = number of relevant links.
import os
import time
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse
from google import genai
from google.genai import types

app = FastAPI()

html_content = """
<!DOCTYPE html>
<html>
<head>
    <title> The Official Torielli Translator</title>

    <!-- MathJax Configuration and Script for Live LaTeX Rendering -->
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            },
            svg: { fontCache: 'global' }
        };
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

    <style>
        body { font-family: sans-serif; max-width: 650px; margin: 40px auto; padding: 20px; text-align: center; color: #222; }
        .upload-box { border: 2px dashed #ccc; padding: 30px; border-radius: 8px; margin-bottom: 20px; }
        
        /* Box for Live Rendered LaTeX Math */
        #renderedResult { background: #ffffff; padding: 20px; border-radius: 8px; border: 1px solid #007acc; text-align: left; min-height: 50px; margin-top: 10px; font-size: 16px; }
        
        /* Box for Raw LaTeX Code */
        #rawCode { background: #f4f4f4; padding: 15px; border-radius: 8px; text-align: left; font-family: monospace; font-size: 13px; white-space: pre-wrap; overflow-x: auto; display: none; margin-top: 10px; border: 1px solid #ddd; }
        
        /* Copy Button Styling */
        .copy-btn { background-color: #007acc; color: white; border: none; padding: 8px 16px; font-size: 14px; border-radius: 4px; cursor: pointer; font-weight: bold; margin-top: 10px; display: none; }
        .copy-btn:hover { background-color: #005999; }
        
        .section-header { text-align: left; margin-top: 20px; font-weight: bold; font-size: 14px; color: #555; }
    </style>
</head>
<body>
    <h1>Torielli Translator v1.0</h1>
    <p>Upload a photo of Torielli handwriting to convert it into readable English and LaTeX code.</p>
    
    <div class="upload-box">
        <input type="file" id="imageInput" accept="image/*">
        <br><br>
        <button onclick="translateImage()" style="padding: 10px 20px; font-size: 16px; cursor: pointer;">Translate Handwriting</button>
    </div>
    
    <h3>Translation Output:</h3>
    <div id="resultStatus">English translation will appear here... Does that make sense? Good.</div>
    
    <div id="renderedResult" style="display: none;"></div>
    
    <button id="copyBtn" class="copy-btn" onclick="copyLaTeX()">Copy Raw LaTeX Code</button>
    
    <div id="rawHeader" class="section-header" style="display: none;">Raw LaTeX Code:</div>
    <pre id="rawCode"></pre>

    <script>
        let currentRawLatex = "";

        async function translateImage() {
            const input = document.getElementById('imageInput');
            const statusDiv = document.getElementById('resultStatus');
            const renderedDiv = document.getElementById('renderedResult');
            const rawPre = document.getElementById('rawCode');
            const copyBtn = document.getElementById('copyBtn');
            const rawHeader = document.getElementById('rawHeader');
            
            if (!input.files[0]) {
                alert('Please select an image first!');
                return;
            }
            
            statusDiv.innerText = "Decoding unknown Torielli hieroglyphics... converting triple-n into normal n... converting quad-m into normal m... converting triangle into lowercase s... finishing converstions...";
            renderedDiv.style.display = "none";
            rawPre.style.display = "none";
            copyBtn.style.display = "none";
            rawHeader.style.display = "none";
            
            const formData = new FormData();
            formData.append('file', input.files[0]);
            
            try {
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    body: formData
                });
                const data = await response.json();
                
                if (data.translation) {
                    statusDiv.innerText = "Translation Complete!";
                    currentRawLatex = data.translation;
                    
                    // Display rendered math using MathJax
                    renderedDiv.innerHTML = data.translation;
                    renderedDiv.style.display = "block";
                    
                    if (window.MathJax) {
                        MathJax.typesetPromise([renderedDiv]).catch((err) => {
                            console.log("MathJax preview error:", err);
                        });
                    }
                    
                    // Display raw code and copy button
                    rawPre.innerText = data.translation;
                    rawPre.style.display = "block";
                    copyBtn.style.display = "inline-block";
                    rawHeader.style.display = "block";
                } else {
                    statusDiv.innerText = "Server Error: " + (data.error || "Unknown response");
                }
            } catch (err) {
                statusDiv.innerText = "Fetch Error: " + err.message;
            }
        }

        function copyLaTeX() {
            navigator.clipboard.writeText(currentRawLatex).then(() => {
                const btn = document.getElementById('copyBtn');
                btn.innerText = "Copied!";
                setTimeout(() => { btn.innerText = "Copy Raw LaTeX Code"; }, 2000);
            }).catch(err => {
                alert("Failed to copy code: " + err);
            });
        }
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def home():
    return html_content

@app.post("/api/translate")
async def translate(file: UploadFile = File(...)):
    try:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return {"error": "GEMINI_API_KEY environment variable is not set on Render!"}

        image_bytes = await file.read()
        client = genai.Client(api_key=api_key)
        
        prompt = """
        You are the official 'Torielli Translator'. Transcribe the handwritten notes in this photo into plain English text.
        
        Known handwriting quirks for this author:
        - Lowercase 'a' looks like the Greek letter theta (θ).
        - Lowercase 's' looks like a triangle (Δ).
        - The number '9' looks like a lowercase 'g'.
        - the number 4 sometimes looks like a european 4. Not always.
        - Most common lowercase letters are cursive. 
        - Additional notes are normally in all caps and print, not cursive.
        
        Additional Instructions:
        - Analyze the context of the subject matter to intelligently fix any handwriting errors or typos.
        - Format mathematical formulas, equations, and structured text using standard inline ($...$) or block ($$...$$) LaTeX expressions.
        - Do NOT include full document wrappers like \\documentclass{article}, \\usepackage{...}, or \\begin{document}. Output only the content itself.
        - Do NOT include markdown fence wrappers like ```latex in your output.
        
        Return ONLY the decoded English text formatted in clean LaTeX math blocks.
        """

        # Fixed candidate models using active supported endpoints
        candidate_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]
        
        last_error = None
        for model in candidate_models:
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=model,
                        contents=[
                            types.Part.from_bytes(data=image_bytes, mime_type=file.content_type or "image/jpeg"),
                            prompt
                        ]
                    )
                    return {"translation": response.text}
                except Exception as model_err:
                    last_error = model_err
                    if "503" in str(model_err) or "UNAVAILABLE" in str(model_err):
                        time.sleep(1.5)
                        continue
                    else:
                        break
        
        return {"error": f"Google AI services are temporarily busy. Details: {str(last_error)}"}

    except Exception as e:
        print(f"Error during translation: {str(e)}")
        return {"error": str(e)}

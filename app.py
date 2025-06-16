import gradio as gr
import uuid
import json
import os
from datetime import datetime
import shutil

# Configuration
JOBS_FILE = "jobs.json"
OUTPUTS_DIR = "outputs"

# Set these to your actual GitHub username/repo for Colab links!
GITHUB_USERNAME = "livinghappy247"  # CHANGE THIS TO YOUR GITHUB USERNAME
GITHUB_REPO = "take-command"        # CHANGE THIS TO YOUR REPO NAME

# Initialize
if not os.path.exists(JOBS_FILE):
    with open(JOBS_FILE, "w") as f:
        json.dump({}, f)

if not os.path.exists(OUTPUTS_DIR):
    os.makedirs(OUTPUTS_DIR)

# Job Management Functions
def load_jobs():
    try:
        with open(JOBS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_jobs(jobs):
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)

def create_job(uploaded_file, pipeline_steps, voice_text="", emotion="neutral", enhancement_type="basic"):
    """Create a new job and save uploaded file"""
    if not uploaded_file:
        return "❌ Please upload a file first!"
    
    job_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save uploaded file
    if hasattr(uploaded_file, "name"):
        file_extension = os.path.splitext(uploaded_file.name)[1]
    else:
        file_extension = ""
    saved_filename = f"{job_id}_{timestamp}_input{file_extension}"
    saved_path = os.path.join(OUTPUTS_DIR, saved_filename)
    shutil.copy2(uploaded_file, saved_path)
    
    # Create job entry
    jobs = load_jobs()
    jobs[job_id] = {
        "id": job_id,
        "created": timestamp,
        "status": "ready",
        "current_step": 0,
        "pipeline": pipeline_steps if pipeline_steps else [],
        "files": {
            "input": saved_filename,
            "current": saved_filename
        },
        "parameters": {
            "voice_text": voice_text,
            "emotion": emotion,
            "enhancement_type": enhancement_type
        },
        "step_outputs": {},
        "logs": [f"{datetime.now().strftime('%H:%M:%S')} - Job created"]
    }
    save_jobs(jobs)
    
    return f"✅ Job {job_id} created successfully!\nFile: {getattr(uploaded_file, 'name', 'Uploaded File')}\nPipeline: {' → '.join(pipeline_steps)}"

def get_job_status():
    """Get formatted status of all jobs"""
    jobs = load_jobs()
    if not jobs:
        return "No jobs found."
    
    status_lines = []
    for job_id, job in jobs.items():
        current_step = job.get('current_step', 0)
        total_steps = len(job.get('pipeline', []))
        status = job.get('status', 'unknown')
        # Status emoji
        status_emoji = {
            'ready': '⏳',
            'processing': '🔄', 
            'completed': '✅',
            'error': '❌',
            'waiting': '⏸️'
        }.get(status, '❓')
        
        status_lines.append(
            f"{status_emoji} **Job {job_id}**\n"
            f"   Status: {status.title()}\n"
            f"   Progress: {current_step}/{total_steps} steps\n"
            f"   Created: {job.get('created', 'Unknown')}\n"
        )
    
    return "\n".join(status_lines)

def generate_colab_links(job_id):
    """Generate Colab notebook links for a job"""
    jobs = load_jobs()
    if job_id not in jobs:
        return "❌ Job not found!"
    
    job = jobs[job_id]
    current_step = job.get('current_step', 0)
    pipeline = job.get('pipeline', [])
    
    if current_step >= len(pipeline):
        return "✅ All steps completed for this job!"
    
    step_name = pipeline[current_step] if pipeline else "General"
    # Notebook mapping
    notebook_map = {
        "Voice Cloning & TTS": "voice_clone.ipynb",
        "Lip Sync & Emotions": "lip_sync.ipynb", 
        "Split & Merge": "split_merge.ipynb",
        "Audio Enhancement": "audio_enhance.ipynb",
        "Video Enhancement": "video_enhance.ipynb"
    }
    notebook_file = notebook_map.get(step_name, "general_process.ipynb")
    params = {
        "job_id": job_id,
        "step": step_name.lower().replace(" ", "_"),
        "input_file": job['files']['current'],
        "voice_text": job['parameters'].get('voice_text', ''),
        "emotion": job['parameters'].get('emotion', 'neutral'),
        "enhancement_type": job['parameters'].get('enhancement_type', 'basic')
    }
    # Construct the Colab URL to directly open the notebook
    base_url = (
        f"https://colab.research.google.com/github/"
        f"{GITHUB_USERNAME}/{GITHUB_REPO}/blob/main/notebooks/{notebook_file}"
    )
    param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    colab_url = f"{base_url}?{param_string}"
    
    # Update job status
    job['status'] = 'waiting'
    job['logs'].append(f"{datetime.now().strftime('%H:%M:%S')} - Colab link generated for {step_name}")
    save_jobs(jobs)
    
    instructions = f"""
🚀 **Ready for Step {current_step + 1}: {step_name}**

**Colab Link:** [Open {notebook_file} in Colab]({colab_url})

**Instructions:**
1. Click the link above to open the Colab notebook
2. Ensure GPU runtime is enabled (Runtime → Change runtime type → GPU)
3. Run all cells in order
4. The notebook will automatically process your file
5. When complete, return here and click "Check Progress"

**Current Input File:** {job['files']['current']}
"""
    return instructions

def mark_step_complete(job_id, output_filename=""):
    """Mark current step as complete and advance to next"""
    jobs = load_jobs()
    if job_id not in jobs:
        return "❌ Job not found!"
    
    job = jobs[job_id]
    current_step = job.get('current_step', 0)
    pipeline = job.get('pipeline', [])
    
    if current_step >= len(pipeline):
        return "✅ Job already completed!"
    
    # Mark step complete
    step_name = pipeline[current_step]
    job['step_outputs'][step_name] = output_filename or f"{job_id}_step_{current_step}_output"
    job['current_step'] += 1
    job['logs'].append(f"{datetime.now().strftime('%H:%M:%S')} - Completed {step_name}")
    
    if output_filename:
        job['files']['current'] = output_filename
    
    # Check if all steps complete
    if job['current_step'] >= len(pipeline):
        job['status'] = 'completed'
        job['logs'].append(f"{datetime.now().strftime('%H:%M:%S')} - All steps completed!")
    else:
        job['status'] = 'ready'
    
    save_jobs(jobs)
    
    if job['status'] == 'completed':
        return f"🎉 Job {job_id} completed successfully!\nFinal output: {job['files']['current']}"
    else:
        next_step = pipeline[job['current_step']]
        return f"✅ Step completed! Next: {next_step}\nClick 'Generate Colab Link' to continue."

def download_result(job_id):
    """Get download link for job result"""
    jobs = load_jobs()
    if job_id not in jobs:
        return None
    
    job = jobs[job_id]
    if job['status'] != 'completed':
        return None
    
    output_file = os.path.join(OUTPUTS_DIR, job['files']['current'])
    if os.path.exists(output_file):
        return output_file
    return None

# Gradio Interface
def create_interface():
    with gr.Blocks(title="Take Command - AI Media Pipeline", theme=gr.themes.Soft()) as demo:
        
        gr.HTML("""
        <div style="text-align: center; padding: 20px;">
            <h1>🎛️ Take Command</h1>
            <h3>AI-Powered Media Processing Pipeline</h3>
            <p>Upload your media files and create custom AI processing workflows</p>
        </div>
        """)
        
        with gr.Tabs():
            
            # Job Creation Tab
            with gr.Tab("📤 Create New Job"):
                with gr.Row():
                    with gr.Column(scale=2):
                        file_input = gr.File(
                            label="Upload Media File (Audio/Video/Image)",
                            file_types=["audio", "video", "image"]
                        )
                        pipeline_steps = gr.CheckboxGroup(
                            choices=[
                                "Voice Cloning & TTS",
                                "Lip Sync & Emotions", 
                                "Split & Merge",
                                "Audio Enhancement",
                                "Video Enhancement"
                            ],
                            label="Select Pipeline Steps (in order)",
                            value=["Voice Cloning & TTS"]
                        )
                    with gr.Column(scale=1):
                        voice_text = gr.Textbox(
                            label="Text for Voice Cloning/TTS",
                            placeholder="Enter text to be spoken...",
                            lines=3
                        )
                        emotion = gr.Dropdown(
                            choices=["neutral", "happy", "sad", "angry", "surprised"],
                            label="Emotion for Lip Sync",
                            value="neutral"
                        )
                        enhancement_type = gr.Dropdown(
                            choices=["basic", "professional", "cinematic"],
                            label="Enhancement Quality",
                            value="basic"
                        )
                create_btn = gr.Button("🚀 Create Job", variant="primary", size="lg")
                creation_output = gr.Textbox(label="Job Creation Status", lines=3)
                create_btn.click(
                    create_job,
                    inputs=[file_input, pipeline_steps, voice_text, emotion, enhancement_type],
                    outputs=creation_output
                )
            
            # Job Management Tab  
            with gr.Tab("📊 Manage Jobs"):
                with gr.Row():
                    with gr.Column():
                        job_id_input = gr.Textbox(
                            label="Job ID",
                            placeholder="Enter job ID (e.g., a1b2c3d4)"
                        )
                        with gr.Row():
                            generate_link_btn = gr.Button("🔗 Generate Colab Link")
                            check_progress_btn = gr.Button("🔄 Check Progress")
                            mark_complete_btn = gr.Button("✅ Mark Step Complete")
                        colab_instructions = gr.Markdown("")
                        step_status = gr.Textbox(label="Step Status", lines=2)
                generate_link_btn.click(
                    generate_colab_links,
                    inputs=job_id_input,
                    outputs=colab_instructions
                )
                check_progress_btn.click(
                    lambda job_id: get_job_status() if not job_id else f"Job {job_id} status updated.",
                    inputs=job_id_input,
                    outputs=step_status
                )
                mark_complete_btn.click(
                    mark_step_complete,
                    inputs=job_id_input,
                    outputs=step_status
                )
            
            # Status & Downloads Tab
            with gr.Tab("📋 Status & Downloads"):
                refresh_btn = gr.Button("🔄 Refresh Status")
                all_jobs_status = gr.Markdown("")
                refresh_btn.click(
                    get_job_status,
                    outputs=all_jobs_status
                )
                with gr.Row():
                    download_job_id = gr.Textbox(label="Job ID for Download")
                    download_btn = gr.Button("📥 Download Result")
                    download_file = gr.File(label="Download")
                download_btn.click(
                    download_result,
                    inputs=download_job_id,
                    outputs=download_file
                )
            
            # Instructions Tab
            with gr.Tab("📖 Instructions"):
                gr.Markdown("""
                ## How to Use Take Command
                
                ### 1. Create a New Job
                - Upload your media file (audio, video, or image)
                - Select the processing steps you want to apply
                - Configure parameters (text for TTS, emotion, enhancement level)
                - Click "Create Job" to get your Job ID
                
                ### 2. Process Your Job
                - Go to "Manage Jobs" tab
                - Enter your Job ID
                - Click "Generate Colab Link" to get the processing notebook
                - Open the Colab link and run all cells (ensure GPU is enabled)
                - Return here and click "Mark Step Complete" when done
                - Repeat for each step in your pipeline
                
                ### 3. Download Results
                - Once all steps are complete, go to "Status & Downloads"
                - Enter your Job ID and click "Download Result"
                
                ### Pipeline Steps Explained
                
                **Voice Cloning & TTS**: Clone a voice from sample audio and generate speech from text
                
                **Lip Sync & Emotions**: Synchronize lip movements with audio and add facial expressions
                
                **Split & Merge**: Automatically split large files for processing and merge results
                
                **Audio Enhancement**: Improve audio quality with denoising and enhancement
                
                **Video Enhancement**: Upscale video resolution and improve visual quality
                
                ### Requirements
                - Google Colab account (free tier works)
                - Hugging Face account for file storage
                - GPU runtime enabled in Colab for best performance
                """)
        
        # Auto-refresh status on load
        demo.load(get_job_status, outputs=all_jobs_status)
    
    return demo

# Launch the app
if __name__ == "__main__":
    demo = create_interface() 
    demo.launch()
  

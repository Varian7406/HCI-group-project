<h1 align="center">Project 11: One Step at a Time</h1>

<br>

<h2 align="left"> Draft Status</h2>
<p align="left">
  <strong>This is a draft version.</strong> It is meant to be used as a backbone for the TBC changes that will be made afterwards. Commands, versions and structure may change.
</p>
<ul>
  <li><strong>Front end:</strong> The Tkinter interface will be stripped out and replaced with a JavaScript/CSS/HTML front end. The project will eventually become a web app.</li>
  <li><strong>Origin:</strong> This draft was made with the help of Qwen 3.7 Plus and Claude Sonnet 5.5.</li>
</ul>

<hr>

<h2 align="left"> Project Purpose & Scenario</h2>
<p align="left">
  Python desktop simulation of a maintenance-guidance experiment. <br>
  Compares three guidance conditions (Manual, Overlay, Explanatory Overlay) to measure completion time, action errors, and response to simulated hazards.
</p>
<p align="left">
  <strong>Simulation Statement:</strong> <strong>TBC.</strong> This is a screen-only desktop simulation. No physical AR headsets, live AI, or real machinery are used. Hazards are pre-scripted events.
</p>

<hr>

<h2 align="left"> Prerequisites & Software Versions</h2>
<p align="left">To ensure reproducibility, this draft requires:</p>
<ul>
  <li><strong>OS:</strong> Ubuntu / Windows (Tested on <strong>TBA</strong>)</li>
  <li><strong>Python:</strong> 3.10+ (exact version <strong>TBA</strong>)</li>
  <li><strong>Tkinter:</strong> System Tcl/Tk runtime (<code>python3-tk</code>) <em>(draft only, to be removed)</em></li>
  <li><strong>Pillow:</strong> version <strong>TBA</strong></li>
  <li><strong>pytest:</strong> version <strong>TBA</strong></li>
</ul>

<hr>

<h2 align="left"> Installation and Setup</h2>
<p align="left">Run the following commands from the repository root:</p>
<pre><code>git clone https://github.com/Varian7406/HCI-group-project.git
cd HCI-group-project
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
python -m pip install -r requirements-dev.txt
</code></pre>

<hr>

<h2 align="left"> Running the Application & Tests</h2>
<p align="left"><strong>Open the app:</strong> <code>python -m project11</code></p>
<p align="left"><strong>Run Practice Mode:</strong> <code>python -m project11 --practice</code> <strong>(Command TBC)</strong></p>
<p align="left"><strong>Run Researcher Session:</strong> <code>python -m project11 --session</code> <strong>(Command TBC)</strong></p>
<p align="left"><strong>Run Tests:</strong> <code>python -m pytest -q</code></p>

<hr>

<h2 align="left"> Data Analysis & Expected Output</h2>
<p align="left">
  <strong>Command:</strong> <code>python -m analysis.analyse --input data/example --output results/example</code> <strong>(TBC)</strong><br>
  <strong>Expected Output:</strong> TBA. (Will output a CSV summary of task completion times and a comparison chart.)
</p>

<hr>

<h2 align="left"> AI Assistance Disclosure</h2>
<p align="left">
  In accordance with the course framework, AI tools were used during this project.<br>
  <strong>Tools used:</strong> Qwen 3.7 Plus, Claude Sonnet 5.5<br>
  <strong>Purposes:</strong> Code assistance, planning, debugging.<br>
  <em>More detailed AI use information will be added towards the end of the project. Current notes are in <code>AI_USE.md</code>.</em>
</p>

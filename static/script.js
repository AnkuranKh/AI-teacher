function showLoader() {
    document.getElementById("loader").style.display = "block";
    document.getElementById("progressText").innerText = "Processing...";
}

function hideLoader() {
    document.getElementById("loader").style.display = "none";

    // ✅ hide progress bar after done
    document.getElementById("progressContainer").style.display = "none";
}

// ✅ NEW FUNCTION
function updateProgress(text) {
    document.getElementById("progressText").innerText = text;
}

//////////////////////////////////////////////////////////
// ✅ NEW: REAL BACKEND PROGRESS TRACKING
//////////////////////////////////////////////////////////

async function trackProgress() {
    let interval = setInterval(async() => {
        try {
            let res = await fetch("/progress/");
            let data = await res.json();

            let bar = document.getElementById("progressBar");
            let status = document.getElementById("progressStatus");

            bar.style.width = data.progress + "%";
            bar.innerText = data.progress + "%";
            status.innerText = data.status;

            if (data.progress >= 100) {
                clearInterval(interval);
            }
        } catch (err) {
            console.log("Progress fetch error:", err);
        }
    }, 1000);
}

//////////////////////////////////////////////////////////

async function upload() {
    let file = document.getElementById("videoFile").files[0];

    if (!file) {
        alert("Please select a file");
        return;
    }

    let formData = new FormData();
    formData.append("file", file);

    showLoader();

    // ✅ SHOW PROGRESS BAR
    document.getElementById("progressContainer").style.display = "block";

    // ✅ START TRACKING
    trackProgress();

    updateProgress("📤 Uploading video...");

    let res = await fetch("/upload/", {
        method: "POST",
        body: formData
    });

    let data = await res.json();

    updateProgress("✅ Done!");

    await new Promise(r => setTimeout(r, 500));

    hideLoader();
    document.getElementById("output").innerText = data.message;
}

//////////////////////////////////////////////////////////
// ✅ NEW: YOUTUBE UPLOAD FUNCTION
//////////////////////////////////////////////////////////

async function uploadYouTube() {
    let url = document.getElementById("youtubeUrl").value;

    if (!url) {
        alert("Please enter a YouTube URL");
        return;
    }

    showLoader();

    // ✅ SHOW PROGRESS BAR
    document.getElementById("progressContainer").style.display = "block";

    // ✅ START TRACKING
    trackProgress();

    updateProgress("⬇️ Downloading YouTube video...");

    let res = await fetch("/upload-youtube/?url=" + encodeURIComponent(url), {
        method: "POST"
    });

    let data = await res.json();

    updateProgress("✅ Done!");

    await new Promise(r => setTimeout(r, 500));

    hideLoader();
    document.getElementById("output").innerText = data.message;
}

//////////////////////////////////////////////////////////
// 🚫 NO CHANGES BELOW (kept exactly same)
//////////////////////////////////////////////////////////

async function ask() {
    let query = document.getElementById("query").value;

    showLoader();
    updateProgress("💭 Understanding question...");

    await new Promise(r => setTimeout(r, 300));

    updateProgress("🔎 Fetching context...");
    await new Promise(r => setTimeout(r, 500));

    updateProgress("🧠 Generating answer...");

    let res = await fetch("/chat/?query=" + encodeURIComponent(query), {
        method: "POST"
    });

    let data = await res.json();

    hideLoader();
    document.getElementById("output").innerText = data.answer;
}

async function getSummary() {
    showLoader();
    updateProgress("📖 Reading transcript...");

    await new Promise(r => setTimeout(r, 400));

    updateProgress("✂️ Summarizing content...");

    let res = await fetch("/summary/");
    let data = await res.json();

    hideLoader();
    document.getElementById("output").innerText = data.summary;
}

async function getQuiz() {
    showLoader();
    updateProgress("📖 Reading transcript...");

    await new Promise(r => setTimeout(r, 400));

    updateProgress("📝 Creating questions...");

    let res = await fetch("/quiz/");
    let data = await res.json();

    hideLoader();
    document.getElementById("output").innerText = data.quiz;
}
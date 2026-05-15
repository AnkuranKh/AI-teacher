function showLoader() {
    document.getElementById("loader").style.display = "block";
}

function hideLoader() {
    document.getElementById("loader").style.display = "none";
    document.getElementById("progressContainer").style.display = "none";
}

function updateProgress(text) {
    document.getElementById("progressText").innerText = text;
}

function getYouTubeEmbedUrl(url) {

    let videoId = "";

    try {

        const urlObj =
            new URL(url);

        // youtube.com/watch?v=
        if (
            urlObj.hostname.includes(
                "youtube.com"
            )
        ) {
            videoId =
                urlObj.searchParams.get(
                    "v"
                );
        }

        // youtu.be/
        else if (
            urlObj.hostname.includes(
                "youtu.be"
            )
        ) {
            videoId =
                urlObj.pathname.substring(
                    1
                );
        }

    } catch (err) {

        return "";
    }

    return `https://www.youtube-nocookie.com/embed/${videoId}?rel=0&modestbranding=1`;
}
async function trackProgress() {
    let interval = setInterval(async() => {
        let res = await fetch("/progress/");
        let data = await res.json();

        let bar = document.getElementById("progressBar");
        let status = document.getElementById("progressStatus");

        bar.style.width = data.progress + "%";
        bar.innerText = data.progress + "%";
        status.innerText = data.status;

        if (data.progress >= 100) clearInterval(interval);
    }, 1000);
}

/* Upload */
async function upload() {

    document.getElementById("chatBox").innerHTML = "";

    let file =
        document.getElementById(
            "videoFile"
        ).files[0];

    if (!file) {
        return alert(
            "Select a file"
        );
    }

    console.log(
        "📁 Upload started"
    );

    // 🎥 SHOW VIDEO
    let videoPlayer =
        document.getElementById(
            "videoPlayer"
        );

    let youtubeContainer =
        document.getElementById(
            "youtubeContainer"
        );

    let youtubePlayer =
        document.getElementById(
            "youtubePlayer"
        );

    // show normal video
    videoPlayer.style.display =
        "block";

    // hide youtube player
    youtubeContainer.style.display =
        "none";

    // reset youtube iframe completely
    youtubeContainer.innerHTML = `
    <iframe
        id="youtubePlayer"
        width="100%"
        height="300"
        style="border:none;"
        frameborder="0"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        referrerpolicy="strict-origin-when-cross-origin"
        allowfullscreen>
    </iframe>
`;

    // keep old working logic
    videoPlayer.src =
        URL.createObjectURL(file);

    videoPlayer.load();

    let formData =
        new FormData();

    formData.append(
        "file",
        file
    );

    showLoader();

    document.getElementById(
        "query"
    ).disabled = true;

    document.getElementById(
            "progressContainer"
        ).style.display =
        "block";

    trackProgress();

    try {

        console.log(
            "🚀 Sending upload request..."
        );

        let res =
            await fetch(
                "/upload/", {
                    method: "POST",
                    body: formData
                }
            );

        console.log(
            "✅ Upload response received"
        );

        let data =
            await res.json();

        console.log(
            "📦 Response data:",
            data
        );

        hideLoader();

        document.getElementById(
            "query"
        ).disabled = false;

        addMessage(
            data.message,
            "ai"
        );

    } catch (err) {

        console.error(
            "❌ Upload failed:",
            err
        );

        hideLoader();

        document.getElementById(
            "query"
        ).disabled = false;

        addMessage(
            "❌ Upload failed. Check Render logs.",
            "ai"
        );
    }
}

/* YouTube */
async function uploadYouTube() {

    document.getElementById(
        "chatBox"
    ).innerHTML = "";

    let url =
        document.getElementById(
            "youtubeUrl"
        ).value.trim();

    if (!url) {
        return alert(
            "Enter URL"
        );
    }

    let videoPlayer =
        document.getElementById(
            "videoPlayer"
        );

    let youtubeContainer =
        document.getElementById(
            "youtubeContainer"
        );

    // hide normal player
    videoPlayer.style.display =
        "none";

    // show youtube area
    youtubeContainer.style.display =
        "block";

    // IMPORTANT FIX:
    // recreate iframe fresh every time
    youtubeContainer.innerHTML = `
        <iframe
            width="100%"
            height="300"
            src="${getYouTubeEmbedUrl(url)}"
            frameborder="0"
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen>
        </iframe>
    `;

    showLoader();

    document.getElementById(
        "query"
    ).disabled = true;

    document.getElementById(
            "progressContainer"
        ).style.display =
        "block";

    trackProgress();

    try {

        let res =
            await fetch(
                "/upload-youtube/?url=" +
                encodeURIComponent(url), {
                    method: "POST"
                }
            );

        let data =
            await res.json();

        hideLoader();

        document.getElementById(
            "query"
        ).disabled = false;

        addMessage(
            data.message,
            "ai"
        );

    } catch (err) {

        console.error(err);

        hideLoader();

        document.getElementById(
            "query"
        ).disabled = false;

        addMessage(
            "❌ Failed to process YouTube video.",
            "ai"
        );
    }
}

/* Ask */
async function ask() {
    let input = document.getElementById("query");
    let query = input.value;
    if (!query) return;

    input.disabled = true;

    addMessage(query, "user");
    showTyping();

    let res = await fetch("/chat/?query=" + encodeURIComponent(query), { method: "POST" });
    let data = await res.json();

    removeTyping();
    addMessage(data.answer, "ai");

    input.disabled = false;
    input.value = "";
}

/* Summary */
async function getSummary() {
    showLoader();
    let res = await fetch("/summary/");
    let data = await res.json();
    hideLoader();

    addMessage("📖 Summary", "user");
    addMessage(data.summary, "ai");
}

/* Quiz */
async function getQuiz() {
    showLoader();
    let res = await fetch("/quiz/");
    let data = await res.json();
    hideLoader();

    addMessage("📝 Quiz", "user");
    addMessage(data.quiz, "ai");
}

/* Chat helpers */
function addMessage(text, sender) {
    let chat = document.getElementById("chatBox");

    let msg = document.createElement("div");
    msg.classList.add("message", sender);
    msg.innerText = text;

    chat.appendChild(msg);
    chat.scrollTop = chat.scrollHeight;
}

/* Typing */
function showTyping() {
    let chat = document.getElementById("chatBox");

    let msg = document.createElement("div");
    msg.classList.add("message", "ai");
    msg.id = "typing";
    msg.innerText = "Typing...";

    chat.appendChild(msg);
}

function removeTyping() {
    let t = document.getElementById("typing");
    if (t) t.remove();
}

/* Enter key */
document.getElementById("query").addEventListener("keypress", function(e) {
    if (e.key === "Enter") ask();
});
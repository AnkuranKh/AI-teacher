function showLoader() {
    document.getElementById("loader").style.display = "block";
}

function hideLoader() {
    document.getElementById("loader").style.display = "none";
}

async function upload() {
    let file = document.getElementById("videoFile").files[0];

    if (!file) {
        alert("Please select a file");
        return;
    }

    let formData = new FormData();
    formData.append("file", file);

    showLoader();

    let res = await fetch("/upload/", {
        method: "POST",
        body: formData
    });

    let data = await res.json();

    hideLoader();
    document.getElementById("output").innerText = data.message;
}

async function ask() {
    let query = document.getElementById("query").value;

    showLoader();

    let res = await fetch("/chat/?query=" + encodeURIComponent(query), {
        method: "POST"
    });

    let data = await res.json();

    hideLoader();
    document.getElementById("output").innerText = data.answer;
}

async function getSummary() {
    showLoader();

    let res = await fetch("/summary/");
    let data = await res.json();

    hideLoader();
    document.getElementById("output").innerText = data.summary;
}

async function getQuiz() {
    showLoader();

    let res = await fetch("/quiz/");
    let data = await res.json();

    hideLoader();
    document.getElementById("output").innerText = data.quiz;
}
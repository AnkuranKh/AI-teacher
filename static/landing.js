// ---------- DEFAULT EXAM ----------

let selectedExam = "upsc";
let selectedTitle = "UPSC";


// ---------- ELEMENTS ----------

const examCards =
    document.querySelectorAll(
        ".exam-card"
    );

const selectedExamText =
    document.getElementById(
        "selectedExam"
    );

const startBtn =
    document.getElementById(
        "startBtn"
    );


// ---------- UPDATE UI ----------

function updateSelection(
    exam,
    title
) {

    selectedExam = exam;
    selectedTitle = title;

    // update selected text
    selectedExamText.innerText =
        title;

    // update button text
    startBtn.innerHTML =
        `🚀 Start ${title} Preparation`;

    // update redirect URL
    startBtn.href =
        `/app?exam=${exam}`;
}


// ---------- CARD CLICK ----------

examCards.forEach(card => {

    card.addEventListener(
        "click",
        () => {

            // remove previous active
            examCards.forEach(c =>
                c.classList.remove(
                    "active"
                )
            );

            // add new active
            card.classList.add(
                "active"
            );

            // get data
            const exam =
                card.dataset.exam;

            const title =
                card.dataset.title;

            // update
            updateSelection(
                exam,
                title
            );
        }
    );

});


// ---------- DEFAULT LOAD ----------

updateSelection(
    selectedExam,
    selectedTitle
);
let input;
let commaPressed = false;

function evaluate_input() {

    let textInput = $("#input");
    let displaydInput = $("#change");
    let userInput = Number(textInput.text().replace(",", "."));

    if (isNaN(userInput)) {
        displaydInput.css("color", "red");
        displaydInput.text("NaN!");
        throw "NaN";
    }

    if (userInput > 0) {
        displaydInput.css("color", "green")
    } else  {
        displaydInput.css("color", "red")
    }
    if(commaPressed)
        displaydInput.text(userInput.toFixed(2) + ' €');
    else
        displaydInput.text(userInput.toFixed(0) + ' €');
    return userInput;
}

document.addEventListener('DOMContentLoaded', function () {

    $('#book').click(function () {
        let amount = evaluate_input();
        let changed = {};
        if(amount !== 0)
        {
            changed['amount'] = amount;
            changed['user'] = Number($('#userID').text()).toFixed(0);
        }
        console.log(changed);
        $.post("/add/credit", JSON.stringify(changed), function () {
             window.location.replace("/work");
        });
    });


    $('#dialPad').find(':button').click(function () {

        console.log($(this));
        const attr = $(this).attr('data-number');
        const sumAsText = $('#input');

        if (typeof attr !== typeof undefined && attr !== false) {
            sumAsText.text(sumAsText.text() + $(this).text());
            evaluate_input();
        }
        else if ($(this).is('#decimalPoint')) {
            commaPressed = true;
            sumAsText.text(sumAsText.text() + $(this).text());
            evaluate_input();
        }
        else if ($(this).is('#minus')) {
            if(sumAsText.text().startsWith("-"))
                sumAsText.text(sumAsText.text().substr(1));
            else{
                sumAsText.text($(this).text() + sumAsText.text());
            }
            evaluate_input();
        }
    });

    $('#resetInput').click(function () {
        $('#change').text("");
        $('#input').text("");
        commaPressed = false;
    });

    $(document).bind('keypress', function(e) {
        const cardID = $('#cardID');
        if(e.which === 13)
        {
            console.log("read: " + cardID.text());
            cardID.text("");
            if(receipt_state['sum'] === 0)
            {
                console.log("einzahlen :)");
                window.location.replace("/balance");
            }
            else
            {
                console.log("abrechnen!")
            }

        }
        else if(e.which > 47 && e.which < 58)
        {
            cardID.append(e.which - 48);
        }
    });


}, false);
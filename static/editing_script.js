$(document).keypress(function(e) {
    var keycode = (e.keyCode ? e.keyCode : e.which);
    if (!(e.shiftKey)) {
        var input = $('input[data-key=' + e.key + ']');
        if (input.length) {
            input.click();
        }
    }
    else {
        switch (e.key) {
            case 'A':
            case 'Ф':
                saveAndClose();
                break;
            case 'S':
            case 'Ы':
                if (saveImage())
                    alert("Разметка для изображения сохранена!");
                break;
            case 'D':
            case 'В':
                closeWindow();
                break;
            case 'F':
            case 'А':
                clearLabeling();
                break;
            case 'G':
            case 'П':
                deleteImage();
                break;
        }
    }
});
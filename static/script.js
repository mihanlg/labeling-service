function postJSON(url, params) {
    var resp = false;
    $.ajax({
        type: "POST",
        data: JSON.stringify(params),
        url: url,
        contentType: "application/json",
        timeout: 1000,
        async: false,
        success: function() {
            resp = true;
        }
    });
    return resp;
}

function saveImage() {
    var classes = [];
    $('input[type=checkbox]').each(function () {
        if (this.checked) {
            classes.push($(this).attr("data-label"));
        }
    });
    var params = {'path': $('img').attr('data-path'), 'classes': classes};
    var ret = postJSON("/save", params);
    if (!ret) {
        alert("Не удается сохранить разметку для изображения!");
    }
    return ret;
}

function deleteImage() {
    if (confirm("Вы уверены, что хотите удалить изображение?")) {
        var params = {'path': $('img').attr('data-path')};
        if (postJSON("/delete", params))
            skipImage();
        else
            alert("Не удалось удалить изображение!")
    }
}

function nextImage() {
    if (saveImage())
        skipImage();
}

function saveAndClose() {
    if (saveImage())
        closeWindow();
}

function skipImage() {
    window.open("/next", "_self");
}

function goBack() {
    window.history.back();
}

function closeWindow() {
    window.close();
}

function clearLabeling() {
    if (confirm("Вы уверены, что хотите сбросить разметку?")) {
        var params = {'path': $('img').attr('data-path')};
        if (postJSON("/clear_labeling", params))
            closeWindow();
        else
            alert("Не удалось сбросить разметку!")
    }
}


function openJSON(url, params) {
    $.ajax({
        type: "POST",
        data: JSON.stringify(params),
        url: url,
        contentType: "application/json",
        timeout: 1000,
        async: false,
        success: function(response) {
            var wnd = window.open("about:blank", "_blank");
            wnd.document.write(response);
            wnd.document.close();
        }
    });
}

function editLabels(img) {
    var path = img.getAttribute('data-path');
    openJSON('/editing_labels', {"path": path});
}

function updatePage() {
    var label_checkboxes = $('.selected_labels input[type=checkbox]:checked');
    var params = "?perpage=10";
    if (label_checkboxes.length) {
        var labels = [];
        label_checkboxes.each(function() {
           labels.push($(this).attr('data-label'));
        });
        params += '&labels=' + labels.join(',');
    }
    window.open("/labeled"+params, "_self");
}
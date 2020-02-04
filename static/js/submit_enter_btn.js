$(window).keydown(function (event) {
    if (event.keyCode == 13) {
        event.preventDefault();
        if ($('.buttonNext').hasClass('buttonDisabled')) {
            $('.buttonFinish').click();
        }
        else
            $("#disb_widget").smartWizard('goForward');
    }
});
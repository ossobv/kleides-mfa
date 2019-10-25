jQuery(function ($) {
    $('#kleides-mfa-show-tokens').on('click', function () {
        $('#kleides-mfa-tokens').toggle().each(function  (index, el) {
            el.style.height = el.scrollHeight + 'px';
        });
    });
});

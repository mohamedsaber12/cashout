$(function() {
    var url = window.location.href;
    console.log(url);
    var user = $('#transaction-table').data('uid');
    if (url.indexOf('en') == -1) {
        url = window.location.href.split('ar')[0].concat('api/secure/trx/').concat(user).concat('/all/')
    }else{
        url = window.location.href.split('en')[0].concat('api/secure/trx/').concat(user).concat('/all/')
    }
    var isFilter = false;
    var user = $('#transaction-table').data('uid');
    var table = $('#transaction-table').DataTable({
        responsive: true,
        destroy: true,
        dom: "<'row'<'col-sm-3'l><'col-sm-2'f><'clear'><'col-sm-offset-7'<'x'>>>" + "<'row'<'col-sm-12'tr>>" + "<'row'<'col-sm-3'i><'col-sm-3 text-center'B><'col-sm-6'p>>",
        buttons: [
                'excel'
        ],
        "processing": true,
        "serverSide": true,
        "ajax": {
            "url": url,
            "data": function ( d ) {
                if (isFilter) {
                    d.from_datetime = $("#from-datepicker").prop('value');
                    d.to_datetime = $("#to-datepicker").prop('value');
                    //isFilter = false;
                }
            }
        },
        "ordering": false,
        "rowCallback": function(row, data, index) {
            if (data[0].indexOf("Failed") > -1) {
                $(row).addClass('danger');
            } else if (data[0].indexOf("Completed") > -1) {
                $(row).addClass('success');
            } else if (data[0].indexOf("Expired") > -1) {
                $(row).addClass('warning');
            } else if (data[0].indexOf("Pending") > -1) {
                $(row).addClass('info');
            }
        }
    });

    var searchbox = $('#transaction-table_filter input');
    searchbox.unbind();
    searchbox.bind('keyup change', function (e) {
        if (e.keyCode == 13) {
            table.search(this.value).draw();
        }
        if (!this.value) {
            table.search('').draw();
        }
    });

    function validate_datetime_input() {
        if (is_dateinput_correct()) {
            isFilter = true;
            table.draw();
        }
        else {
            $("#from-datepicker").val('');
            $("#to-datepicker").val('');
        }
    }

    function is_dateinput_correct() {
        var regexpattern = /\d\d-\d\d-\d\d\d\d/;
        var fromvalue = $("#from-datepicker").prop('value');
        var tovalue = $("#to-datepicker").prop('value');

        return regexpattern.test(tovalue) && regexpattern.test(fromvalue);
    }

    $("div.x").html('<div id="filter-div">From <input type="text" id="from-datepicker" class="form-control input-sm date-picker-input"><span id="totext">To</span> <input type="text" id="to-datepicker" class="form-control input-sm date-picker-input"><a class="btn btn-default" id="filter-btn">Filter</a><a class="btn btn-default" id="refresh-btn"><i class="fa fa-refresh fa-fw"></i></a></div>');

    $("#from-datepicker").datepicker({
        controlType: 'select',
        timeFormat: "hh:mm TT",
        dateFormat: "dd-mm-yy",
        onClose: function(selectedDate) {
            $("#to-datepicker").datepicker("option", "minDate", selectedDate);
        }
    });

    $("#to-datepicker").datepicker({
        controlType: 'select',
        timeFormat: "hh:mm TT",
        dateFormat: "dd-mm-yy",
    });

    $("#filter-btn").on('click', function() {
        validate_datetime_input();
    });

    $("#refresh-btn").on('click', function() {
        $("#from-datepicker").val('');
        $("#to-datepicker").val('');
        //$('#transaction-table_filter input').val('');
        isFilter = false;
        table.search('').draw();
    });

});
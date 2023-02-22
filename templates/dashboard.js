$(document).ready(function () {
    var socket = io.connect();
    socket.on('update-fdo', function(msg){
        console.log('FDO message received');
        $('#fdo').html(msg.data);

    });
    socket.on('update-dms', function(msg){
        console.log('DMS message received');
        $('#dms').html(msg.data);


    });
    socket.on('update-thingsboard', function(msg){
        console.log('Thingsboard message received');
        $('#thingsboard').html(msg.data);

    });
    socket.on('update-bkc', function(msg){
        console.log('BKC message received');
        $('#bkc').html(msg.data);

    });
});
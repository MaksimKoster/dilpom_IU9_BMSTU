var express = require('express');
var app = express();
app.use(express.static('public'));

const { createClient } = require('@clickhouse/client');

const client = createClient({
    host: 'http://92.53.105.143:18123',
    username: 'default',
    password: '',
  })

app.get('/:startTime/:endTime', async function(req, res) {
    let t = req.params.startTime
    let r = req.params.endTime

    var q = 'SELECT * FROM security_db.detection WHERE (time_detect BETWEEN \'' + t + '\' AND \''+ r +'\')'

    const resultSet = await client.query({
        query: q,
        format: 'JSONEachRow',
      })
    const dataset = await resultSet.json()
    res.send(dataset)
})

var server = app.listen(11000, function () {
    var host = "92.53.105.143"
    console.log('Version: ' + process.version);
    if (process.argv[2]) {
      console.log('Command Port: ' + process.argv[2]);
      host = process.argv[2]
    } else {
      console.log('Using default port');
    }
    var port = server.address().port
    console.log("Image server listening at http://%s:%s", host, port)
})
const express = require('express');
const cors = require('cors');
const app = express();

app.use(cors());

// Proxies requests to the official FPL API
// By using app.use, req.url automatically captures everything after '/api'
app.use('/api', async (req, res) => {
  const data = await fetch(`https://fantasy.premierleague.com/api${req.url}`).then(r => r.json());
  res.json(data);
});

// Serves your frontend files
app.get('/', (req, res) => res.sendFile(__dirname + '/public/index.html'));
app.use(express.static('public'));

app.listen(3000, () => console.log('Server running at: http://localhost:3000'));
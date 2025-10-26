const express = require("express");
const mysql = require("mysql2/promise");
const cors = require("cors");
const multer = require("multer");
const path = require("path");

//const bcrypt = require("bcryptjs");

const app = express();
//app.use(express.json());
app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use('/files',express.static('E:/certificates'));
// ✅ Serve static files (so PDFs can be accessed via browser)
app.use("/uploads", express.static(path.join(__dirname, "uploads")));

// Connect to MySQL
const pool = mysql.createPool({
    host: "localhost",
    user: "root",      // change if needed
    password: "Root*19470",      // your MySQL password
    database: "notice_board",
       //waitForConnections: true,
     // connectionLimit: 10,
       //queueLimit: 0
});


(async () => {
    try {
        const connection = await pool.getConnection(); // test one connection from pool
        console.log("✅ MySQL Connected...");
        connection.release(); // release it back to pool
    } catch (err) {
        console.error("❌ MySQL Connection Error:", err.message);
    }
})();



app.get('/api/timetable', async (req, res) => {
   const { semester, type } = req.query;
   console.log("📌 Incoming request:", semester, type);
   if (!semester || !type) {
        return res.status(400).json({ error: "Missing semester or type" });
    }

  db.query(
    "SELECT file_url FROM timetables WHERE semester = ? AND type = ?",
    [semester, type],
    (err, results) => {
      if (err) {
        console.error("❌ DB Error:", err);
        return res.status(500).json({ error: err.message });
      }
      if (results.length === 0) {
         console.warn("⚠️ No results found");
        return res.status(404).json({ error: "Not found" });
      }
      console.log("✅ Found:", results[0]);
      res.json({ file_url: results[0].file_url });
    }
  );
});
app.listen(3000, () => {
    console.log('Server running on http://localhost:3000');
});
app.post('/login', async (req, res) => {
    const { usn, password } = req.body;
    console.log("🔹 Login request:", { usn,password });

    if (!usn || !password) {
        return res.status(400).json({ error: "All fields are required" });
    }
    console.log("Running query for USN:", usn, "and date:", password);


    try {
        const [rows] = await pool.query(
            "SELECT * FROM users WHERE usn = ? AND password_date = ?",
            //['2vd23cs034', '2025-09-26']
            [usn, password]
        );
        console.log("🔹 Query result:", rows);

        if (rows.length === 0) {
            return res.status(401).json({ error: "Invalid USN or password" });
        }

        const user = rows[0];
        
        console.log("✅ Login success:", user.usn);

        
        // Login success
        return res.json({
            user: {
                usn: user.usn,
                password: user.password_date,

                isAdmin: user.is_admin === 1 // convert to boolean
            }
        });

    } catch (err) {
        console.error("❌ Login error:", err.message);
        res.status(500).json({ error: "Server error" });

    }
   // res.json({ success: true, received: req.body });
    
});



app.listen(5000, () => console.log("🚀 Server running on port 5000"));

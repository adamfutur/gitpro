require('dotenv').config();
const { GoogleGenerativeAI } = require('@google/generative-ai');


const API_KEY = process.env.GEMINI_API_KEY;
console.log("Testing with API Key:", API_KEY ? "Found" : "Missing");

const genAI = new GoogleGenerativeAI(API_KEY);

async function run() {
    const models = ["gemini-2.5-flash"];

    for (const modelName of models) {
        console.log(`\nTesting model: ${modelName}`);
        try {
            const model = genAI.getGenerativeModel({ model: modelName });
            const result = await model.generateContent("Hello");
            console.log(`✅ Success with ${modelName}:`, (await result.response).text());
            return; // Stop on first success
        } catch (error) {
            console.error(`❌ Failed with ${modelName}: ${error.message}`);
            if (error.message.includes("404")) {
                console.log("   (Model not found or not supported)");
            }
        }
    }
    console.log("\nAll models failed.");
}

run();

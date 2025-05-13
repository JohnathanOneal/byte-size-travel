// fill out handle bars templates with json data 
import fs from 'fs';
import Handlebars from 'handlebars';
import path from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

// Get current directory (ES modules don't have __dirname)
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load .env file from parent directory
const envPath = path.join(__dirname, '..', '.env');
dotenv.config({ path: envPath });

// Load paths from environment variables with fallbacks
const templatePath = process.env.TEMPLATE_PATH || path.join(__dirname, 'template.html');
const dataPath = process.env.DATA_PATH || path.join(__dirname, 'data.json');
const outputPath = process.env.OUTPUT_PATH || path.join(__dirname, 'output.html');

// 1. Load the template file
const templateSource = fs.readFileSync(templatePath, 'utf-8');
console.log(`Template loaded from: ${templatePath}`);

// 2. Compile the Handlebars template
const template = Handlebars.compile(templateSource);

// 3. Load the JSON data
const data = JSON.parse(fs.readFileSync(dataPath, 'utf-8'));
console.log(`Data loaded from: ${dataPath}`);

// 4. Process the template with the data
const processedHTML = template(data);

// 5. Output the result to a file
fs.writeFileSync(outputPath, processedHTML);

console.log(`HTML output successfully written to: ${outputPath}`);
import fs from 'fs';
import Handlebars from 'handlebars';
import path from 'path';
import { createReadStream } from 'fs';
import { createInterface } from 'readline';
import dotenv from 'dotenv';

dotenv.config({ path: '../.env' });

const template = Handlebars.compile(fs.readFileSync(process.env.WEB_TEMPLATE_ONE_FILE, 'utf8'));
const outputPath = process.env.WEBSITE_NEWSLETTER_DIR

export async function processLines() {
  const rl = createInterface({ input: createReadStream(process.env.UNPROCESSED_TEXT_FILE) });

  for await (const line of rl) {
    if (!line.trim()) continue;
    
    const data = JSON.parse(fs.readFileSync(line.trim(), 'utf8'));
    fs.writeFileSync(outputPath, template(data), 'utf8');
  }
}

processLines();

// File: clean-json.js

import { readFile, writeFile, mkdir } from 'fs/promises';
import path from 'path';

/**
 * Checks if a value is a string that represents a JSON array.
 * @param {any} value The value to check.
 * @returns {boolean} True if the value is a string-encoded JSON array.
 */
function isStringifiedJsonArray(value) {
    return typeof value === 'string' && value.startsWith('[') && value.endsWith(']');
}

/**
 * Cleans the data by parsing double-encoded JSON arrays.
 * @param {Array<Record<string, any>>} data The array of objects to process.
 * @returns {Array<Record<string, any>>} The cleaned array of objects.
 */
function cleanData(data) {
    return data.map((item) => {
        const cleanedItem = {};

        for (const key in item) {
            // why: we only want to process the object's own properties.
            if (Object.prototype.hasOwnProperty.call(item, key)) {
                const value = item[key];

                if (isStringifiedJsonArray(value)) {
                    try {
                        // why: attempt to parse the string into a real array.
                        cleanedItem[key] = JSON.parse(value);
                    } catch (e) {
                        // why: if parsing fails, keep the original value to avoid data loss.
                        cleanedItem[key] = value;
                        console.warn(`Could not parse value for key "${key}", keeping original.`);
                    }
                } else {
                    cleanedItem[key] = value;
                }
            }
        }
        return cleanedItem;
    });
}

/**
 * Main function to run the script.
 * @param {string} inputPath The path to the input JSON file.
 */
async function main(inputPath) {
    if (!inputPath) {
        console.error('Error: Please provide a path to the input JSON file.');
        process.exit(1);
    }

    try {
        const fileContent = await readFile(inputPath, 'utf-8');
        const data = JSON.parse(fileContent);

        if (!Array.isArray(data)) {
             throw new Error('Input file content is not a JSON array.');
        }

        const convertedData = cleanData(data);
        
        const inputDir = path.dirname(inputPath);
        const outputDir = path.join(inputDir, 'dist');
        
        // why: ensure the relative output directory exists before writing to it.
        await mkdir(outputDir, { recursive: true });

        const inputFilename = path.basename(inputPath);
        const outputPath = path.join(outputDir, inputFilename);

        // why: pretty-print the JSON output for better readability.
        await writeFile(outputPath, JSON.stringify(convertedData, null, 2));

        console.log(`✅ Successfully converted file. Output saved to: ${outputPath}`);
    } catch (error) {
        console.error(`❌ An error occurred: ${error.message}`);
        process.exit(1);
    }
}

// why: get the file path from the command-line arguments.
const inputFile = process.argv[2];
main(inputFile);
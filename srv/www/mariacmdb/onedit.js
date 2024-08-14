//
// onedit.js - update an SQL row after it is updated in a browser
//
async function onEdit(newRow) {
  console.log("onEdit() newRow: ", newRow); 
  const url = "http://localhost/mariacmdb/restapi.py/count"; 
  const requestBody = {                    // Prepare the request body
    data: newRow
  };
  try {                                    // Send the POST request to replace the row
    const response = await fetch(url, {
      body: JSON.stringify(requestBody),   // Convert data to JSON 
      headers: {
        "Authorization": "Bearer your-api-token", // Include auth token if needed
        "Content-Type": "application/json" // Specify the content type
      },
      method: "POST"  
    });
    if (!response.ok) {                    // Check if response is OK (status code 200-299)
      throw new Error(`ERROR: ${response.status} - ${response.statusText}`);
    }
    const result = await response.json();  // Parse and return response as JSON
    return result;
  } 
  catch (error) {
    console.error("ERROR: failed to replace row: ", error);
    throw error;                           // Rethrow error to handle it in calling function
  }
}

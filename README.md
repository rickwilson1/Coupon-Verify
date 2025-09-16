# Coupon-Verify
Input address to see if it falls within city and/or just county jurisdiction
First uses Google Geocordinates API (Rick Wilson's) to get geocordinates
Then uses the Official GIS REST service URL for Each County or City to determine if coorindates fit within boundaries
JSON file containes URL for Counties and Cities.  
Coordinates from County GIS are prioritized in program.

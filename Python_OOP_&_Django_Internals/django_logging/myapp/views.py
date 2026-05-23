from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import time

def home(request):
    """Simple home page view"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Request Logger Demo</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            h1 { color: #333; }
            ul { list-style-type: none; padding: 0; }
            li { margin: 10px 0; }
            a {
                display: inline-block;
                padding: 10px 20px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
            a:hover { background-color: #0056b3; }
            .log-info {
                background-color: #e9ecef;
                padding: 15px;
                border-radius: 5px;
                margin-top: 20px;
            }
            code {
                background-color: #333;
                color: #fff;
                padding: 2px 5px;
                border-radius: 3px;
            }
        </style>
    </head>
    <body>
        <h1> Request Logger Middleware Demo</h1>
        <p>Check the <code>logs/requests.log</code> file to see request logging in action!</p>
        
        <h2>Test Endpoints:</h2>
        <ul>
            <li><a href="/test/"> Normal Request</a></li>
            <li><a href="/slow/"> Slow Request (1s delay)</a></li>
            <li><a href="/error/"> Error Request (404)</a></li>
            <li><a href="/json/"> JSON Response</a></li>
            <li><a href="/user-agent/"> Show User-Agent</a></li>
        </ul>
        
        <div class="log-info">
            <strong> Log Format:</strong><br>
            <code>Timestamp | IP | Method | Path | Status | Time(ms) | User-Agent</code>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html_content)

def test_view(request):
    """Test view that returns a simple response"""
    return HttpResponse(" This is a test request! Check the logs.")

def slow_view(request):
    """Simulate a slow request"""
    time.sleep(1)  # Simulate processing time
    return HttpResponse(" This request took 1 second to process! Check the logs to see the time.")

def error_view(request):
    """Simulate an error response"""
    return HttpResponse(" This is a 404 error page!", status=404)

@csrf_exempt
def json_view(request):
    """Return JSON response"""
    data = {
        'message': 'This is a JSON response',
        'status': 'success',
        'timestamp': str(time.time())
    }
    return JsonResponse(data)

def user_agent_view(request):
    """Echo back user agent information"""
    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
    return HttpResponse(f" Your User-Agent is:<br><code>{user_agent}</code>")
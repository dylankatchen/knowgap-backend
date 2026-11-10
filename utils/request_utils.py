from quart import jsonify


def not_text_response():
    """400 for a request body with a field that isn't text. Fields that go into
    database queries must be text, since a JSON object such as {"$ne": null}
    would act as a filter instead of a value."""
    return jsonify({
        'error': 'Invalid request',
        'message': 'Request fields must be text',
        'statusCode': 400
    }), 400

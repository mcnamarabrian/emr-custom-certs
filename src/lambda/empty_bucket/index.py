import boto3
import cfnresponse

def handler(event, context):
    bucket = event['ResourceProperties']['BucketName']

    if event['RequestType'] == 'Delete':
        try:
            s3 = boto3.resource('s3')
            bucket_obj = s3.Bucket(bucket)
            bucket_obj.object_versions.delete()
            print(f"Successfully emptied bucket: {bucket}")
            cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
        except Exception as e:
            print(f"Error emptying bucket: {e}")
            cfnresponse.send(event, context, cfnresponse.FAILED, {'Error': str(e)})
    else:
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {})
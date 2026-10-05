"""Deploy the trained sklearn model to a SageMaker real-time endpoint (illustrative, untested here).

Prereqs: pip install sagemaker boto3; an execution role ARN; model tarball uploaded to S3.
    python scripts/deploy_sagemaker.py --model-s3 s3://bucket/model.tar.gz --role arn:aws:iam::123:role/SageMakerRole
The tarball must contain model.joblib and an inference.py exposing model_fn/input_fn/predict_fn/output_fn.
"""
import argparse


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-s3", required=True)
    ap.add_argument("--role", required=True)
    ap.add_argument("--name", default="clopidogrel-response")
    ap.add_argument("--instance", default="ml.m5.large")
    a = ap.parse_args()
    from sagemaker.sklearn import SKLearnModel

    model = SKLearnModel(model_data=a.model_s3, role=a.role, entry_point="inference.py",
                         framework_version="1.2-1", py_version="py3")
    model.deploy(initial_instance_count=1, instance_type=a.instance, endpoint_name=a.name)


if __name__ == "__main__":
    main()

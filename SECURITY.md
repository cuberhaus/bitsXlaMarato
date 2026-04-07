# Security Policy — bitsXlaMarato

## Reporting a Vulnerability
If you discover a security vulnerability, please email polcg10@gmail.com. Do not open a public issue.

## Security Considerations

### No Authentication
- FastAPI backend (port 8001) and Angular frontend (port 4200) have **no authentication**.
- Anyone with network access can upload videos/frames and trigger analysis.
- Add authentication before deploying beyond a local or trusted network.

### File Upload Security
- Video and frame uploads are a high-risk attack surface:
  - Validate file types (MIME type and magic bytes) — only accept expected video/image formats.
  - Enforce file size limits to prevent disk exhaustion and denial-of-service.
  - Sanitize filenames to prevent path traversal attacks.
  - Store uploads in a non-web-accessible directory.
  - Be aware that malformed video/image files can exploit processing libraries (OpenCV, PIL).

### Medical Image Data
- The project processes medical imaging data (surgical video frames for Mask R-CNN analysis).
- Do not use real patient data without proper de-identification and institutional approval.
- Do not log or expose image/video data in error responses.
- Implement data retention policies — delete processed frames and results when no longer needed.

### Container Security
- Review the Dockerfile and base images for known vulnerabilities.
- Pin image versions — avoid `latest` tags.
- Do not run containers as root if avoidable.
- Keep dependencies updated, especially OpenCV and deep learning libraries.

### Recommendations
- Bind services to `127.0.0.1` for local-only access.
- Use HTTPS for any non-local deployment.
- Pin Python dependencies and audit them regularly.
- Monitor resource usage — video processing and ML inference can be resource-intensive and exploitable for DoS.

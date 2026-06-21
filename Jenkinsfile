pipeline {
  agent any

  triggers {
    cron('0 8 * * 1-5')
  }

  options {
    timeout(time: 60, unit: 'MINUTES')
    ansiColor('xterm')
    timestamps()
  }

  parameters {
    string(name: 'GITHUB_PROJECT_OWNER', defaultValue: 'github-user-name', trim: true)
    string(name: 'GITHUB_PROJECT_OWNER_TYPE', defaultValue: 'user', trim: true)
    string(name: 'GITHUB_PROJECT_NUMBER', defaultValue: '1', trim: true)
    string(name: 'GITHUB_PROJECT_FILTER', defaultValue: 'sprint:@current is:issue state:open assignee:@me', trim: true)

    text(
      name: 'GITHUB_USERS',
      defaultValue: 'github-username:email@example.com',
      description: 'One GitHub user per line. Format: github-username:email@example.com'
    )

    string(name: 'OUTPUT_FORMAT', defaultValue: 'html', trim: true)

    string(name: 'SMTP_HOST', defaultValue: 'smtp.gmail.com', trim: true)
    string(name: 'SMTP_PORT', defaultValue: '587', trim: true)
    string(name: 'SMTP_USE_TLS', defaultValue: 'true', trim: true)
    string(name: 'SMTP_USE_SSL', defaultValue: 'false', trim: true)
    string(name: 'SMTP_FROM', defaultValue: 'email@example.com', trim: true)
    string(name: 'SMTP_SUBJECT', defaultValue: 'GitHub Project Digest', trim: true)

  }

  environment {
    DOCKER_IMAGE = 'wesleydean/github-project-digest:edge'
  }

  stages {
    stage('Run GitHub Project Digest') {
      steps {
        withCredentials([
          string(credentialsId: 'id-of-secret-with-github-pat', variable: 'GITHUB_TOKEN'),
          usernamePassword(
            credentialsId: 'REPLACE_WITH_SMTP_CREDENTIAL_ID',
            usernameVariable: 'SMTP_USERNAME',
            passwordVariable: 'SMTP_PASSWORD'
          )
        ]) {
          sh '''
set +x
set -eu
umask 077

printf "%s\\n" "$GITHUB_USERS" | while IFS= read -r GITHUB_USER ; do
  [ -n "$GITHUB_USER" ] || continue

cat > .env <<EOF

GITHUB_TOKEN=${GITHUB_TOKEN}
GITHUB_PROJECT_OWNER=${GITHUB_PROJECT_OWNER}
GITHUB_PROJECT_OWNER_TYPE=${GITHUB_PROJECT_OWNER_TYPE}
GITHUB_PROJECT_NUMBER=${GITHUB_PROJECT_NUMBER}
GITHUB_PROJECT_FILTER=${GITHUB_PROJECT_FILTER}
GITHUB_USER=${GITHUB_USER}
OUTPUT_FORMAT=${OUTPUT_FORMAT}

SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT}
SMTP_USE_TLS=${SMTP_USE_TLS}
SMTP_USE_SSL=${SMTP_USE_SSL}
SMTP_USERNAME=${SMTP_USERNAME}
SMTP_PASSWORD=${SMTP_PASSWORD}
SMTP_FROM=${SMTP_FROM}
SMTP_SUBJECT=${SMTP_SUBJECT}
EOF

  docker run --env-file .env --rm "${DOCKER_IMAGE}"

  rm -f .env
        done
'''
        }
      }
    }
  }

  post {
    always {
      sh '''
set +e
rm -f .env
'''
    }
  }
}

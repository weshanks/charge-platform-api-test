pipeline {
    agent any

    stages {
        stage('拉取代码') {
            steps {
                checkout scm
            }
        }
        stage('安装依赖') {
            steps {
                sh 'pip install -r requirements.txt'
            }
        }
        stage('接口自动化') {
            steps {
                sh 'pytest --alluredir=./allure-results'
            }
            post {
                always {
                    allure includeProperties: false, results: [[path: 'allure-results']]
                }
            }
        }
    }

    post {
        always {
            echo '质量门禁：核心用例通过率 100%，整体不低于 98% 才允许继续；失败需先区分环境问题、脚本问题或真实缺陷，不允许靠删用例拉通过率。'
        }
    }
}

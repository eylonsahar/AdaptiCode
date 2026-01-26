"""API routes for AdaptiCode system and minimal HTML views."""
from flask import request, jsonify, render_template
import time
from datetime import datetime

from backend.data.data_manager import DataManager
from backend.business_logic.irt_engine import IRTEngine
from backend.business_logic.user_model_manager import UserModelManager
from backend.business_logic.selection_engine import SelectionEngine
from backend.business_logic.test_runner import TestRunner
from backend.business_logic.feedback_manager import FeedbackManager
from backend.business_logic.llm_gateway import LLMGateway
from backend.business_logic.code_quality_scorer import CodeQualityScorer
from backend.business_logic.pass_fail_evaluator import PassFailEvaluator
from backend.config import Config


# Initialize components (singleton pattern)
data_manager = None
user_model_manager = None
selection_engine = None
test_runner = None
feedback_manager = None
llm_gateway = None
code_quality_scorer = None
pass_fail_evaluator = None


def initialize_components():
    """Initialize all business logic components."""
    global data_manager, user_model_manager, selection_engine
    global test_runner, feedback_manager, llm_gateway, code_quality_scorer, pass_fail_evaluator
    
    if data_manager is None:
        print(f"AdaptiCode starting with USER_MODE={Config.USER_MODE}")
        data_manager = DataManager(Config.DATA_DIR)
        user_profile = data_manager.get_user_profile()
        prerequisite_graph = data_manager.get_prerequisite_graph()
        
        user_model_manager = UserModelManager(user_profile, prerequisite_graph)
        selection_engine = SelectionEngine(data_manager, user_model_manager)
        test_runner = TestRunner()
        feedback_manager = FeedbackManager()
        llm_gateway = LLMGateway()
        code_quality_scorer = CodeQualityScorer(llm_gateway)
        pass_fail_evaluator = PassFailEvaluator(llm_gateway)


def register_routes(app):
    """Register all HTML and API routes."""
    
    @app.before_request
    def before_request():
        """Initialize components before first request."""
        initialize_components()
    
    # ------------------------------------------------------------------
    # Simple HTML pages
    # ------------------------------------------------------------------
    @app.route('/', endpoint='home')
    def home():
        """Cover page with basic marketing copy and a CTA to practice."""
        return render_template('index.html')
    
    @app.route('/question', endpoint='question_page')
    def question_page():
        """Single question page with adaptive question selection."""
        question = selection_engine.select_next_question()
        if not question:
            # If for some reason the question is missing, fall back to home.
            return render_template('index.html')
        
        # Get the selection explanation
        selection_explanation = selection_engine.get_last_selection_explanation()
        
        # Map core fields into a simple structure the template expects.
        # Use a medium difficulty and a default time limit for now.
        question_view = {
            'id': question.name,
            'name': question.name,
            'difficulty': '2',
            'time_limit_minutes': 20,
            'description': question.description,
            'tests': [{'input': t.input, 'output': t.output} for t in question.tests],
            'init_code': question.init_code
        }
        category = question.topic
        
        return render_template(
            'question.html',
            question=question_view,
            category=category,
            selection_explanation=selection_explanation
        )
    
    @app.route('/dashboard', endpoint='dashboard')
    def dashboard():
        """Dashboard page showing user progress, history, and statistics."""
        return render_template('dashboard.html')
    
    @app.route('/guide', endpoint='guide')
    def guide():
        """Platform guide page with explanations and help."""
        return render_template('guide.html')
    
    # ------------------------------------------------------------------
    # JSON API endpoints
    # ------------------------------------------------------------------
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            'status': 'healthy',
            'user_mode': Config.USER_MODE,
            'timestamp': datetime.now().isoformat()
        })
    
    @app.route('/api/question/next', methods=['GET'])
    def get_next_question():
        """
        Get the next adaptive question.
        
        Returns:
            Question details with metadata
        """
        try:
            question = selection_engine.select_next_question()
            
            if not question:
                return jsonify({
                    'error': 'No suitable question found',
                    'message': 'You may have completed all available questions or need to unlock new topics.'
                }), 404
            
            # Get selection explanation
            explanation = selection_engine.get_selection_explanation(question)
            
            # Get current user state
            topic = question.topic
            theta = user_model_manager.get_theta(topic)
            progress = user_model_manager.get_topic_progress(topic)
            
            return jsonify({
                'question': {
                    'name': question.name,
                    'topic': question.topic,
                    'description': question.description,
                    'tests': [{'input': t.input, 'output': t.output} for t in question.tests]
                },
                'metadata': {
                    'your_theta': round(theta, 2),
                    'question_difficulty': round(question.b, 2),
                    'selection_reason': explanation['reason'],
                    'topic_progress': progress
                }
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # ------------------------------------------------------------------
    # Thin wrappers for the question page JS
    # ------------------------------------------------------------------
    @app.route('/check_code', methods=['POST'])
    def check_code():
        """Run tests for the question page without exposing full API."""
        try:
            data = request.json or {}
            question_id = data.get('question_id')
            code = data.get('code')
            
            if not question_id or not code:
                return jsonify({'success': False, 'message': 'Missing code or question_id'}), 400
            
            question = data_manager.get_question(question_id)
            if not question:
                return jsonify({'success': False, 'message': 'Question not found'}), 404
            
            results = test_runner.run_tests(code, question, include_hidden=False)
            summary = test_runner.get_test_summary(results)
            success = bool(results.get('all_passed'))
            visible_tests = results.get('visible_tests', [])
            
            return jsonify({
                'success': success,
                'message': summary,
                'results': results,
                'visible_tests': visible_tests,
            })
        
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/get_hint', methods=['POST'])
    def get_hint():
        """Get a hint for the current question without revealing the solution."""
        try:
            data = request.json or {}
            question_id = data.get('question_id')
            user_code = data.get('code', '')
            hint_number = data.get('hint_number', 1)
            
            if not question_id:
                return jsonify({'success': False, 'message': 'Missing question_id'}), 400
            
            question = data_manager.get_question(question_id)
            if not question:
                return jsonify({'success': False, 'message': 'Question not found'}), 404
            
            # Generate hint using LLM
            hint = llm_gateway.generate_hint(question, user_code, hint_number)
            
            return jsonify({
                'success': True,
                'hint': hint,
                'hint_number': hint_number
            })
        
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/submit_feedback', methods=['POST'])
    def submit_feedback_simple():
        """Accept feedback and render a summary page.

        This endpoint runs hidden tests, stubs an LLM pass/fail decision,
        updates the user model, and then renders a summary page.
        """
        try:
            data = request.json or {}

            question_metadata = data.get('question_metadata') or {}
            question_id = question_metadata.get('id')
            user_code = data.get('user_code')

            if not question_id or not user_code:
                return jsonify({'success': False, 'message': 'Missing user_code or question_id'}), 400

            question = data_manager.get_question(question_id)
            if not question:
                return jsonify({'success': False, 'message': 'Question not found'}), 404

            topic = question.topic
            theta_before = user_model_manager.get_theta(topic)
            status_before = user_model_manager.get_concept_status(topic)

            # Run hidden tests (and visible tests as part of the run)
            test_results = test_runner.run_tests(user_code, question, include_hidden=True)
            hidden_tests = test_results.get('hidden_tests', [])
            hidden_total = len(hidden_tests)
            hidden_passed = sum(1 for t in hidden_tests if t.get('passed'))
            hidden_pass_rate = (hidden_passed / hidden_total) if hidden_total > 0 else 0.0

            # Code quality scoring
            question_context = f"Question: {question.name}\nTopic: {question.topic}\nDescription: {question.description}"
            code_quality_result = code_quality_scorer.score_code_quality(user_code, question_context)
            code_quality_score = code_quality_result.get('Score', 'N/A')
            code_quality_explanation = code_quality_result.get('Explanation', 'No explanation provided')
            code_quality_numeric = code_quality_scorer.get_numeric_score(code_quality_score)

            # Time taken is no longer tracked
            time_taken_seconds = 0.0

            subjective_feedback = {
                'difficulty_rating': data.get('difficulty_rating'),
                'pain_points': data.get('pain_points', []),
                'self_feelings': data.get('self_feelings', ''),
            }
            
            # Get hints_used from submission data
            hints_used = data.get('hints_used', 0)

            # LLM decision for pass/fail
            pass_fail_result = pass_fail_evaluator.evaluate_pass_fail(
                user_code=user_code,
                question=question,
                hidden_pass_rate=hidden_pass_rate,
                code_quality_score=code_quality_score,
                code_quality_explanation=code_quality_explanation,
                theta_before=theta_before,
                hidden_tests=hidden_tests,
                subjective_feedback=subjective_feedback,
                hints_used=hints_used
            )
            ui = pass_fail_result['decision']
            pass_fail_explanation = pass_fail_result['explanation']
            correct = bool(ui)

            # Add code quality to test_results so it gets stored in AnswerRecord
            test_results['code_quality'] = code_quality_score
            test_results['code_quality_numeric'] = code_quality_numeric
            test_results['code_quality_explanation'] = code_quality_explanation

            user_model_manager.record_answer(
                question,
                correct,
                time_taken_seconds,
                test_results,
                subjective_feedback
            )

            data_manager.update_user_profile(user_model_manager.get_profile())

            theta_after = user_model_manager.get_theta(topic)
            status_after = user_model_manager.get_concept_status(topic)

            data_manager.log_interaction('feedback_submit', {
                'question_name': question.name,
                'topic': topic,
                'hidden_pass_rate': hidden_pass_rate,
                'ui': ui,
                'pass_fail_explanation': pass_fail_explanation,
                'code_quality_score': code_quality_score,
                'code_quality_numeric': code_quality_numeric,
                'code_quality_explanation': code_quality_explanation,
            })

            return render_template(
                'summary.html',
                question_name=question.name,
                topic=topic,
                hidden_tests=hidden_tests,
                hidden_total=hidden_total,
                hidden_passed=hidden_passed,
                hidden_pass_rate=hidden_pass_rate,
                ui=ui,
                pass_fail_explanation=pass_fail_explanation,
                theta_before=theta_before,
                theta_after=theta_after,
                status_before=status_before,
                status_after=status_after,
                code_quality_score=code_quality_score,
                code_quality_explanation=code_quality_explanation,
                code_quality_numeric=code_quality_numeric,
            )
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
    
    @app.route('/api/question/<question_name>', methods=['GET'])
    def get_question(question_name):
        """
        Get a specific question by name.
        
        Args:
            question_name: Name of the question
        """
        try:
            question = data_manager.get_question(question_name)
            
            if not question:
                return jsonify({'error': 'Question not found'}), 404
            
            return jsonify({
                'name': question.name,
                'topic': question.topic,
                'description': question.description,
                'tests': [{'input': t.input, 'output': t.output} for t in question.tests]
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/code/submit', methods=['POST'])
    def submit_code():
        """
        Submit code for testing.
        
        Request body:
            - question_name: Name of question
            - code: User's code
            - start_time: When user started (ISO format)
        
        Returns:
            Test results and feedback
        """
        try:
            data = request.json
            question_name = data.get('question_name')
            code = data.get('code')
            start_time_str = data.get('start_time')
            
            if not question_name or not code:
                return jsonify({'error': 'Missing required fields'}), 400
            
            # Get question
            question = data_manager.get_question(question_name)
            if not question:
                return jsonify({'error': 'Question not found'}), 404
            
            # Time taken is no longer tracked
            time_taken = 0.0
            
            # Run tests
            test_results = test_runner.run_tests(code, question, include_hidden=True)
            
            # Process feedback (without subjective feedback for now)
            feedback_result = feedback_manager.process_feedback(
                question, test_results, time_taken
            )
            
            # Update user model
            correct = test_results.get('all_passed', False)
            user_model_manager.record_answer(
                question, correct, time_taken, test_results
            )
            
            # Save updated profile
            data_manager.update_user_profile(user_model_manager.get_profile())
            
            # Log interaction
            data_manager.log_interaction('code_submit', {
                'question_name': question_name,
                'correct': correct,
                'time_taken': time_taken,
                'pass_rate': test_results.get('pass_rate', 0)
            })
            
            # Get updated progress
            progress = user_model_manager.get_topic_progress(question.topic)
            
            return jsonify({
                'test_results': {
                    'success': test_results.get('success'),
                    'all_passed': test_results.get('all_passed'),
                    'passed_tests': test_results.get('passed_tests'),
                    'total_tests': test_results.get('total_tests'),
                    'visible_tests': test_results.get('visible_tests', []),
                    'hidden_tests_summary': {
                        'total': len(test_results.get('hidden_tests', [])),
                        'passed': sum(1 for t in test_results.get('hidden_tests', []) if t['passed'])
                    }
                },
                'feedback': feedback_result,
                'progress': progress,
                'summary': test_runner.get_test_summary(test_results)
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/feedback/submit', methods=['POST'])
    def submit_feedback():
        """
        Submit subjective feedback.
        
        Request body:
            - question_name: Name of question
            - difficulty_rating: 1-5 (1=easy, 5=hard)
            - confidence_level: 1-5 (1=low, 5=high)
            - notes: Optional text feedback
        """
        try:
            data = request.json
            question_name = data.get('question_name')
            
            if not question_name:
                return jsonify({'error': 'Missing question_name'}), 400
            
            # Find the most recent answer for this question
            profile = user_model_manager.get_profile()
            recent_answer = None
            
            for record in reversed(profile.answer_history):
                if record.question_name == question_name:
                    recent_answer = record
                    break
            
            if not recent_answer:
                return jsonify({'error': 'No recent answer found for this question'}), 404
            
            # Update the answer record with subjective feedback
            recent_answer.subjective_feedback = {
                'difficulty_rating': data.get('difficulty_rating'),
                'confidence_level': data.get('confidence_level'),
                'notes': data.get('notes', '')
            }
            
            # Save updated profile
            data_manager.update_user_profile(profile)
            
            # Log interaction
            data_manager.log_interaction('feedback_submit', {
                'question_name': question_name,
                'difficulty_rating': data.get('difficulty_rating'),
                'confidence_level': data.get('confidence_level')
            })
            
            return jsonify({
                'success': True,
                'message': 'Feedback recorded successfully'
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/progress', methods=['GET'])
    def get_progress():
        """
        Get user progress and learning state.
        
        Returns:
            Overall progress, topic progress, recent performance
        """
        try:
            overall = user_model_manager.get_overall_progress()
            
            # Get progress for each topic
            topics_progress = {}
            for topic in data_manager.get_all_topics():
                topics_progress[topic] = user_model_manager.get_topic_progress(topic)
            
            # Recent performance
            recent = user_model_manager.get_recent_performance(10)
            
            return jsonify({
                'overall': overall,
                'topics': topics_progress,
                'recent_performance': recent
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/dashboard/data', methods=['GET'])
    def get_dashboard_data():
        """
        Get comprehensive dashboard data.
        
        Returns:
            Complete answer history, theta values, mastery thresholds, and statistics
        """
        try:
            profile = user_model_manager.get_profile()
            
            # Get answer history (ordered oldest to newest - reverse chronological order)
            answer_history = []
            for record in profile.answer_history:
                # Extract test pass rate from test_results
                test_pass_rate = 0.0
                if record.test_results:
                    passed = record.test_results.get('passed_tests', 0)
                    total = record.test_results.get('total_tests', 1)
                    test_pass_rate = (passed / total * 100) if total > 0 else 0.0
                
                # Extract code quality score
                code_quality = 'N/A'
                if record.test_results and 'code_quality' in record.test_results:
                    code_quality = record.test_results['code_quality']
                
                # Extract subjective feedback
                self_feelings = ''
                if record.subjective_feedback:
                    self_feelings = record.subjective_feedback.get('self_feelings', '')
                    if not self_feelings:
                        # Try other fields
                        difficulty = record.subjective_feedback.get('difficulty_rating', '')
                        pain_points = record.subjective_feedback.get('pain_points', [])
                        if difficulty:
                            self_feelings = f"Difficulty: {difficulty}"
                        if pain_points:
                            self_feelings += f" | Pain points: {', '.join(pain_points)}"
                
                answer_history.append({
                    'question_name': record.question_name,
                    'topic': record.topic or 'Unknown',
                    'test_pass_rate': round(test_pass_rate, 1),
                    'code_quality': code_quality,
                    'self_feelings': self_feelings,
                    'passed': record.correct,
                    'theta_before': round(record.theta_before, 2),
                    'theta_after': round(record.theta_after, 2)
                })
            
            # Get current theta values and mastery thresholds for each topic
            # Use prerequisite graph order to maintain consistent ordering
            prerequisite_graph = data_manager.get_prerequisite_graph()
            topics_data = {}
            for topic in prerequisite_graph.all_concepts:
                current_theta = profile.theta_by_topic.get(topic, 0.0)
                concept_status = profile.concept_status.get(topic, 'locked')
                
                topics_data[topic] = {
                    'current_theta': round(current_theta, 2),
                    'initial_theta': 0.0,
                    'mastery_threshold': Config.MASTERY_THRESHOLD,
                    'status': concept_status,
                    'progress_percent': min(100, (current_theta / Config.MASTERY_THRESHOLD) * 100) if Config.MASTERY_THRESHOLD > 0 else 0
                }
            
            # Calculate statistics
            total_questions = len(answer_history)
            passed_questions = sum(1 for record in answer_history if record['passed'])
            success_rate = (passed_questions / total_questions * 100) if total_questions > 0 else 0
            
            # Topic-wise statistics (also in prerequisite graph order)
            topic_stats = {}
            for topic in prerequisite_graph.all_concepts:
                topic_records = [r for r in answer_history if r['topic'] == topic]
                topic_total = len(topic_records)
                topic_passed = sum(1 for r in topic_records if r['passed'])
                topic_success_rate = (topic_passed / topic_total * 100) if topic_total > 0 else 0
                
                topic_stats[topic] = {
                    'total_attempted': topic_total,
                    'passed': topic_passed,
                    'success_rate': round(topic_success_rate, 1)
                }
            
            return jsonify({
                'answer_history': answer_history,
                'topics': topics_data,
                'statistics': {
                    'total_questions': total_questions,
                    'passed_questions': passed_questions,
                    'success_rate': round(success_rate, 1),
                    'topic_stats': topic_stats
                }
            })
        
        except Exception as e:
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/explanation', methods=['GET'])
    def get_explanation():
        """
        Get LLM explanation for a question.
        
        Query params:
            - question_name: Name of question
        """
        try:
            question_name = request.args.get('question_name')
            
            if not question_name:
                return jsonify({'error': 'Missing question_name parameter'}), 400
            
            question = data_manager.get_question(question_name)
            if not question:
                return jsonify({'error': 'Question not found'}), 404
            
            # Get user's theta for this topic
            theta = user_model_manager.get_theta(question.topic)
            
            # Get attempt count
            attempt_count = data_manager.get_question_attempt_count(question_name)
            
            # Build context
            context = {
                'previous_attempts': attempt_count
            }
            
            # Generate explanation
            explanation = llm_gateway.generate_explanation(question, theta, context)
            
            # Also generate a hint
            hint = llm_gateway.generate_hint(question, attempt_count + 1)
            
            return jsonify({
                'explanation': explanation,
                'hint': hint,
                'attempt_number': attempt_count + 1
            })
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/code/run', methods=['POST'])
    def run_code():
        """Run raw code in a sandbox (used for free-form execution/debugging)."""
        try:
            from backend.business_logic.code_executor import CodeExecutor
            
            data = request.json or {}
            code = data.get('code') or ''
            
            if not code.strip():
                return jsonify({'success': False, 'output': '', 'error': 'Missing code'}), 400
            
            executor = CodeExecutor()
            result = executor.execute(code)
            
            return jsonify(result)
        
        except Exception as e:
            return jsonify({'success': False, 'output': '', 'error': str(e)}), 500
    
    @app.route('/api/concepts/tree', methods=['GET'])
    def get_concept_tree():
        """
        Get prerequisite graph with current status.
        
        Returns:
            Concept tree with status and progress
        """
        try:
            graph = data_manager.get_prerequisite_graph()
            profile = user_model_manager.get_profile()
            
            # Build tree structure
            tree = {
                'concepts': []
            }
            
            for concept in graph.all_concepts:
                status = profile.concept_status.get(concept)
                theta = profile.theta_by_topic.get(concept, 0)
                progress = user_model_manager.get_topic_progress(concept)
                
                tree['concepts'].append({
                    'name': concept,
                    'status': status,
                    'theta': round(theta, 2),
                    'progress_percent': progress['progress_percent'],
                    'prerequisites': graph.get_prerequisites(concept),
                    'level': graph.get_concept_level(concept)
                })
            
            return jsonify(tree)
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/topics', methods=['GET'])
    def get_topics():
        """Get all available topics."""
        try:
            topics = data_manager.get_all_topics()
            
            topics_data = []
            for topic in topics:
                questions = data_manager.get_questions_by_topic(topic)
                stats = data_manager.get_topic_statistics(topic)
                
                topics_data.append({
                    'name': topic,
                    'question_count': len(questions),
                    'statistics': stats
                })
            
            return jsonify({'topics': topics_data})
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/questions/recommended', methods=['GET'])
    def get_recommended_questions():
        """
        Get recommended questions for a topic.
        
        Query params:
            - topic: Topic name
            - n: Number of recommendations (default 5)
        """
        try:
            topic = request.args.get('topic')
            n = int(request.args.get('n', 5))
            
            if not topic:
                return jsonify({'error': 'Missing topic parameter'}), 400
            
            questions = selection_engine.get_recommended_questions(topic, n)
            
            questions_data = []
            for q in questions:
                theta = user_model_manager.get_theta(topic)
                explanation = selection_engine.get_selection_explanation(q)
                
                questions_data.append({
                    'name': q.name,
                    'topic': q.topic,
                    'difficulty': round(q.b, 2),
                    'difficulty_level': explanation['difficulty_level'],
                    'probability_correct': explanation['probability_correct']
                })
            
            return jsonify({'recommendations': questions_data})
        
        except Exception as e:
            return jsonify({'error': str(e)}), 500


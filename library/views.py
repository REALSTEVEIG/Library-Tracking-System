from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer
from rest_framework.decorators import action
from django.utils import timezone
from .tasks import send_loan_notification

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer

    def get_queryset(self):
        return Book.objects.select_related('author').all()

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer

    @action(detail=True, method=['post'])
    def extend_due_date(self, request, pk=None):
        loan = self.get_object()

        if loan.is_returned:
            return Response({'error': 'Loan already returned'}, status=status.HTTP_400_BAD_REQUEST)
        
        if loan.due_date <= timezone.now().date():
            return Response({'error': 'Cannot Extend overdue loan'}, status=status.HTTP_400_BAD_REQUEST)
        
        additional_days = request.data.get('additional_days')
        if not additional_days or not isinstance(additional_days, int) or additional_days <= 0:
            return Response({'error': 'Additional days must be a positive integer'}, status=status.HTTP_400_BAD_REQUEST)
        
        loan.due_date += timedelta(days=additional_days)
        loan.save()

        serializer = self.get_serializer(loan)

        return Response({
            'status': f'Due date extended by {additional_days} days',
            'new_due_dat': loan.due_date,
            'loan': serializer.data
        }, status=status.HTTP_200_OK)

class TopActiveMembersView(APIView):
    def get(self, request):
        top_members = Member.objects.annotate(
            active_loans=Count('loans', filter=models.Q(loans__is_returned=FALSE)).order_by('-active_loans', 'user__username')[:5]

            data = [{
                'id': member.id,
                "username": member.username,
                "email": member.user.email,
                "active_loans": member.active_loans or 0
            }
            for member in top_members
            ]

            return Response(data)
        )
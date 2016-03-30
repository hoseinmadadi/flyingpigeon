SUBROUTINE CGETRS1_F95( A, IPIV, B, TRANS, INFO )
!
!  -- LAPACK95 interface driver routine (version 3.0) --
!     UNI-C, Denmark; Univ. of Tennessee, USA; NAG Ltd., UK
!     September, 2000
!
!  .. USE STATEMENTS ..
   USE LA_PRECISION, ONLY: WP => SP
   USE LA_AUXMOD, ONLY: LSAME, ERINFO
   USE F77_LAPACK, ONLY: GETRS_F77 => LA_GETRS
!  .. IMPLICIT STATEMENT ..
   IMPLICIT NONE
!  .. SCALAR ARGUMENTS ..
   CHARACTER(LEN=1), INTENT(IN), OPTIONAL :: TRANS
   INTEGER, INTENT(OUT), OPTIONAL :: INFO
!  .. ARRAY ARGUMENTS ..
   INTEGER, INTENT(IN) :: IPIV(:)
   COMPLEX(WP), INTENT(INOUT) :: A(:,:), B(:)
!  .. PARAMETERS ..
   CHARACTER(LEN=8), PARAMETER :: SRNAME = 'LA_GETRS'
!  .. LOCAL SCALARS ..
   CHARACTER(LEN=1) :: LTRANS
   INTEGER    :: LINFO, NRHS, N, LD
!  .. INTRINSIC FUNCTIONS ..
   INTRINSIC SIZE, MAX, PRESENT
!  .. EXECUTABLE STATEMENTS ..
   LINFO = 0; N = SIZE(A, 1); NRHS = 1; LD = MAX(1,N)
   IF(PRESENT(TRANS))THEN; LTRANS = TRANS; ELSE; LTRANS='N'; END IF
!  .. TEST THE ARGUMENTS
   IF( SIZE( A, 2 ) /= N .OR. N < 0 ) THEN; LINFO = -1
   ELSE IF( SIZE( IPIV ) /= N ) THEN; LINFO = -2
   ELSE IF( SIZE( B ) /= N ) THEN; LINFO = -3
   ELSE IF(.NOT.LSAME(LTRANS,'N') .AND. .NOT.LSAME(LTRANS,'T').AND. &
           .NOT.LSAME(LTRANS,'C'))THEN; LINFO = -4
   ELSE
!  .. CALL LAPACK77 ROUTINE
      CALL GETRS_F77( LTRANS, N, NRHS, A, LD, IPIV, B, LD, LINFO )
   END IF
   CALL ERINFO( LINFO, SRNAME, INFO )
END SUBROUTINE CGETRS1_F95

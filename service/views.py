import json
import datetime

from django.template import Context, Template
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate
from django.http import (
    HttpResponse,
    HttpResponseBadRequest
)
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render_to_response
from django.utils import timezone
from django.template.loader import get_template

from mechanic.models import Mechanic
from customer.models import Customer
from vehical.models import (
    Vehical,
    OtherService
)
from service.models import (
    Service,
    Payment
)
from parts.models import Part


@require_http_methods(["GET"])
@login_required(login_url='/')
def service_add(request):
    if request.method == "GET":
        context = RequestContext(request, {
            "customers": Customer.objects.filter(is_active=True),
            "mechanics": Mechanic.objects.filter(is_active=True)})
        return render_to_response('service/service.html',
                                  context_instance=context)


@require_http_methods(["POST"])
@login_required(login_url='/')
def service_create(request):
    if request.method == "POST":
        data = request.POST.dict()
        forms = json.loads(data.keys()[0])
        customer_form = forms.get('customer')
        service_form = forms.get('service_deatils')
        mechanic_id = forms.get('mechanic')
        gender = forms.get('gender')
        if customer_form.get('radio1'):
            del customer_form['radio1']
        customer = Customer.objects.filter(
            **customer_form)
        if not customer:
            customer_form['created_by'] = request.user
            customer_form['gender'] = gender
            customer_obj = Customer.objects.create(**customer_form)
        else:
            customer_obj = customer[0]

        if forms.get("service_type") == "vechiacl":
            vehical_form = forms.get("service_type_form")
            vehical_form['customer'] = customer_obj
            vehical = Vehical.objects.filter(**vehical_form)
            if not vehical:
                vehical_form['created_by'] = request.user
                vehical_form['last_serviced_date'] = timezone.now()
                vehical = Vehical.objects.create(**vehical_form)
            else:
                vehical = vehical[0]
                vehical.last_serviced_date = timezone.now()
                vehical.save()
            service_form['vehical'] = vehical

        if forms.get("service_type") == "other":
            other_form = forms.get("service_type_form")
            other_form['customer'] = customer_obj
            other_form['created_by'] = request.user
            other_form['created_at'] = timezone.now()
            other_obj = OtherService.objects.create(**other_form)
            service_form['otherservice'] = other_obj

        if mechanic_id:
            service_form['serviced_by'] = Mechanic.objects.get(id=mechanic_id)
        service_form['created_by'] = request.user
        service_form['customer'] = customer_obj
        service_form['expected_delivery_date'] = datetime.datetime.strptime(
            service_form['expected_delivery_date'], "%m/%d/%Y").date()
        advance_payment = False
        if service_form.get('advance_payment'):
            if service_form.get('advance_payment') > 0:
                service_form['advance_payment'] = int(
                    service_form.get('advance_payment'))
                advance_payment = True
                payment = Payment.objects.create(
                    payment_amount=int(service_form.get('advance_payment')),
                    recieved_by=request.user)
        else:
            service_form['advance_payment'] = 0

        service = Service.objects.create(**service_form)
        if advance_payment:
            service.payment.add(payment)
            service.total_paid = int(service_form.get('advance_payment'))
            service.save()
        obj=list(Service.objects.filter(
            invoice_number=service.invoice_number).values())
        json.JSONEncoder.default=lambda self, obj: (
            obj.isoformat() if isinstance(obj, datetime.datetime) else None)
        return HttpResponse(json.dumps(obj), content_type="application/json")


@require_http_methods(["GET"])
@login_required(login_url='/')
def service_search(request):
    if request.method == "GET":
        context = RequestContext(request, {
            "services": Service.objects.filter(
                is_active=True).only("invoice_number",
                                     "customer",
                                     "vehical",
                                     "is_serviced",
                                     "service_date",
                                     "total_pending",
                                     "total_paid")})
        return render_to_response('service/servicesearch.html',
                                  context_instance=context)


@require_http_methods(["GET"])
@login_required(login_url='/')
def service_view(request, id):
    if request.method == "GET":
        service_obj = Service.objects.filter(invoice_number=id)
        if service_obj:
            context = RequestContext(request, {
                "service": service_obj[0]})
            return render_to_response('service/viewservice.html',
                                      context_instance=context)
        return HttpResponseRedirect("/home/")


@require_http_methods(["GET"])
@login_required(login_url='/')
def service_pending(request):
    if request.method == "GET":
        context = RequestContext(request, {
            "services": Service.objects.filter(
                is_active=True, is_serviced=False)})
        return render_to_response('service/pendingservice.html',
                                  context_instance=context)


@require_http_methods(["GET", "POST"])
@login_required(login_url='/')
def service_edit(request, id):
    if request.method == "GET":
        service_obj = Service.objects.filter(invoice_number=id)
        if service_obj:
            context = RequestContext(request, {
                "service": service_obj[0]})
            return render_to_response('service/editservice.html',
                                      context_instance=context)
        return HttpResponseRedirect("/home/")
    if request.method == "POST":
        return HttpResponse("EDit")


@require_http_methods(["GET"])
@login_required(login_url='/')
def invoice_get(request, id):
    if request.method == "GET":
        service_obj = Service.objects.filter(invoice_number=id)
        if service_obj:
            context = RequestContext(request, {
                "service": service_obj[0]})
            return render_to_response('service/invoice.html',
                                      context_instance=context)
        return HttpResponseRedirect("/home/")
    if request.method == "POST":
        return HttpResponse("EDit")


@require_http_methods(["GET", "POST"])
@login_required(login_url='/')
def create_invoice(request):
    if request.method == "GET":
        service_objs = Service.objects.filter(
            is_serviced=False, is_active=True)
        context = RequestContext(request, {
            "services": service_objs})
        return render_to_response('service/invoicecreate.html',
                                  context_instance=context)

    if request.method == "POST":
        return HttpResponse("EDit")


@require_http_methods(["GET", "POST"])
@login_required(login_url='/')
def invoice(request):
    if request.method == "POST":
        request_dict = request.POST.dict()
        data = json.loads(request_dict.keys()[0])
        service_obj = Service.objects.filter(
            invoice_number=data.get('service_id'))
        if service_obj:
            service_obj = service_obj[0]
            if not service_obj.is_serviced:
                service_obj.is_serviced = True
                service_obj.labour_cost = data.get('labour_cost', 0)
                service_obj.tax = data.get('tax', 0)
                service_obj.total_cost = data.get('total_cost', 0)
                service_obj.remark = data.get('remark', "")
                if data.get('next_service_date'):
		        service_obj.next_service_date = datetime.datetime.strptime(
		            data.get('next_service_date'), "%m/%d/%Y").date()
                service_obj.delivery_date = timezone.now()
                service_obj.total_paid += int(data.get('total_paid', 0))
                payment = Payment.objects.create(payment_amount=data.get('total_paid'),
                                                 recieved_by=request.user)
                total_pending = int(
                    data.get('total_cost', 0)) - int(data.get('total_paid', 0))
                total_pending -= service_obj.advance_payment 
                service_obj.total_pending = total_pending
                if total_pending < 1:
                    service_obj.complete_payment = True                    

                part_data = data.get('part_data')
                part_obj = []
                part_total_cost = 0
                for part in part_data:
                    if part.get('part_name') and part.get('price'):
                        obj = Part.objects.create(part_name=part.get('part_name'),
                                                  price=part.get('price'),
                                                  part_quantity=part.get(
                                                      'part_quantity'),
                                                  created_by=request.user)
                        part_total_cost += (int(obj.price)
                                            * int(obj.part_quantity))
                        part_obj.append(obj)
                service_obj.parts.add(*part_obj)
                service_obj.payment.add(payment)
                service_obj.part_cost = part_total_cost
                service_obj.save()
                return HttpResponse("EDit Complete")
            return HttpResponseRedirect("/home/")


@require_http_methods(["POST"])
@login_required(login_url='/')
def pending_payment(request):
    if request.method == "POST":
        request_dict = request.POST.dict()
        data = json.loads(request_dict.keys()[0])
        service_obj = Service.objects.filter(invoice_number=data.get('service_id'))
        if service_obj:
            service_obj = service_obj[0]
            if service_obj.is_serviced:
                pending_amount = service_obj.total_pending - data.get('pending_payment')
                payment = Payment.objects.create(payment_amount=data.get('pending_payment'),
                                                 recieved_by=request.user)
                if pending_amount == 0:
                    service_obj.complete_payment = True

                service_obj.total_paid += data.get('pending_payment')
                service_obj.total_pending = pending_amount
                service_obj.payment.add(payment)
                service_obj.save()
                return HttpResponse("Pending payment Complete") 
            return HttpResponseRedirect("/home/")


@require_http_methods(["GET"])
@login_required(login_url='/')
def invoice_view(request, id):
    if request.method == "GET":
        service_obj = Service.objects.filter(is_active=True, invoice_number=id)
        if service_obj:
            context = RequestContext(request, {
                "service": service_obj[0]})
            return render_to_response('service/invoicepdf.html',
                                      context_instance=context)


@require_http_methods(["GET", "POST"])
@login_required(login_url='/')
def report(request):
    if request.method == "GET":
        context = RequestContext(request, {})
        return render_to_response('service/report.html',
                                  context_instance=context)
    if request.method == "POST":
        request_dict = request.POST.dict()
        from_date = datetime.datetime.strptime(request_dict.get("from_date"), "%m/%d/%Y")
        till_date = datetime.datetime.strptime(request_dict.get("till_date"), "%m/%d/%Y")
        if request_dict.get('pending'):
            complete_payment = False
        else:
            complete_payment = True

        service_obj = Service.objects.filter(service_date__gt=from_date,
                                             service_date__lt=till_date,
                                             complete_payment=complete_payment,
                                             is_serviced=True)
        template = get_template('service/reportview.html')
        context = Context({'services': service_obj, 'from': from_date,
                           "till": till_date})
        content = template.render(context)
        return HttpResponse(content)


@require_http_methods(["GET", "POST"])
@login_required(login_url='/')
def customer_report(request):
    if request.method == "GET":
        context = RequestContext(request, {
            "customers": Customer.objects.filter(is_active=True)
            })
        return render_to_response('service/customerreport.html',
                                  context_instance=context)
    if request.method == "POST":
        request_dict = dict(request.POST.iterlists())
        customer_id = request_dict.get("customer_id")
        pending = request_dict.get("pending")
        if pending:
            complete_payment = False
        else:
            complete_payment = True

        customer_obj = Customer.objects.get(id=customer_id[0])

        service_obj = Service.objects.filter(customer=customer_obj,
                                             is_serviced=True)
        template = get_template('service/customerreportview.html')
        context = Context({'services': service_obj, 'customer': customer_obj})
        content = template.render(context)
        return HttpResponse(content)


@require_http_methods(["GET"])
@login_required(login_url='/')
def invoice_list(request):
    if request.method == "GET":
        context = RequestContext(request, {
            "services": Service.objects.filter(
                is_active=True,
                is_serviced=True).only("invoice_number",
                                       "customer",
                                       "vehical",
                                       "is_serviced",
                                       "service_date",
                                       "total_pending",
                                       "total_paid")})
        return render_to_response('service/listinvoice.html',
                                  context_instance=context)


@require_http_methods(["GET"])
@login_required(login_url='/')
def customer_report_generate(request, id):
    if request.method == "GET":
        customer_obj = Customer.objects.get(id=id)

        service_obj = Service.objects.filter(customer = customer_obj,
                                             is_serviced=True)
        total_cost = 0
        total_paid = 0
        total_pending = 0
        for service in service_obj:
            total_cost += service.total_cost
            total_paid += service.total_paid
            total_pending += service.total_pending

        context = RequestContext(request, {
            'services': service_obj,
            'customer': customer_obj,
            'total_pending': total_pending,
            'total_paid': total_paid,
            'total_cost': total_cost})
        return render_to_response('service/customerreportpdf.html',
                          context_instance=context)


@require_http_methods(["GET", "POST"])
@login_required(login_url='/')
def report_generate(request):
    if request.method == "POST":
        request_dict = request.POST.dict()
        from_date = datetime.datetime.strptime(request_dict.get("from_date"), "%m/%d/%Y")
        till_date = datetime.datetime.strptime(request_dict.get("till_date"), "%m/%d/%Y")
        if request_dict.get('pending'):
            complete_payment = False
        else:
            complete_payment = True

        service_obj = Service.objects.filter(service_date__gt=from_date,
                                             service_date__lt=till_date,
                                             complete_payment=complete_payment,
                                             is_serviced=True)

        total_cost = 0
        total_paid = 0
        total_pending = 0
        for service in service_obj:
            total_cost += service.total_cost
            total_paid += service.total_paid
            total_pending += service.total_pending

        context = RequestContext(request, {
            "services": service_obj,
            "from_date": from_date.date(),
            "till_date": till_date.date(),
            'total_pending': total_pending,
            'total_paid': total_paid,
            'total_cost': total_cost})
        return render_to_response('service/reportpdf.html',
                          context_instance=context)
